#!/usr/bin/env python3
"""
Up to 4x VL53L1X -> sensor_msgs/LaserScan on /tof_<name>/scan (same message type and shape
as the sim: 2 rays ~1e-6 rad apart so angle_increment is finite).

ALL VL53L1X boards power up at 0x29. To use more than one on a bus you must hold every
XSHUT low, then bring sensors up ONE AT A TIME and give each a new address. The address is
lost on power-off, so this runs every start. Needs one free GPIO per sensor for XSHUT
(fill in `xshut_chips`/`xshut_lines` from `gpioinfo`; I do not know which header pins are
free on your wiring diagram). I could not verify that the TOF400C board breaks XSHUT out --
check the silkscreen. If it doesn't, you need a TCA9548A I2C mux instead.

Single-sensor mode: a sensor whose xshut line is -1 is NOT disabled; it is used as-is at its
configured address (set that address to 0x29 for a lone sensor). With two or more sensors on
one bus, every sensor needs an XSHUT line.

I2C bus: set by the `bus` parameter (Linux bus number, e.g. 4 for /dev/i2c-4) via
adafruit_extended_bus.ExtendedI2C, so it is independent of Blinka's default bus (I2C8).

libgpiod: your old Debian notes pin Python gpiod to v1.6.3, but Ubuntu 24.04 may ship v1 OR v2
(I could not verify which package version your image has; one vendor wiki for another RK board says its
Ubuntu 24 apt package is v1 and `pip install gpiod` pulls v2). This node detects the API at runtime
(`hasattr(gpiod, "request_lines")` => v2) and supports both. XSHUT is only ever driven low or released.

Invalid readings: the Adafruit library returns None for "no target / invalid". We publish
NaN for that (costmap ignores NaN: no marking, no clearing). Publishing +inf would CLEAR
obstacles in the costmap on a black/absorbent/sunlit surface that the sensor simply failed
to see. Set none_as: inf only if you accept that.
"""
import math
import time
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan


class XShut:
    """Drive XSHUT low (sensor off) or release it to high-Z (board pull-up turns sensor on).
    Works with libgpiod v1 (chip.get_line) and v2 (request_lines)."""
    def __init__(self, gpiod, chip_path, line):
        self.g, self.path, self.line = gpiod, chip_path, line
        self.v2 = hasattr(gpiod, 'request_lines')
        self.req = None
        if not self.v2:
            self.chip = gpiod.Chip(chip_path)
            self.l = self.chip.get_line(line)

    def _release(self):
        if self.v2:
            if self.req is not None:
                self.req.release()
                self.req = None
        else:
            try:
                self.l.release()
            except Exception:
                pass

    def disable(self):
        self._release()
        if self.v2:
            from gpiod.line import Direction, Value
            self.req = self.g.request_lines(
                self.path, consumer='tof_xshut',
                config={self.line: self.g.LineSettings(direction=Direction.OUTPUT,
                                                       output_value=Value.INACTIVE)})
        else:
            self.l.request(consumer='tof_xshut', type=self.g.LINE_REQ_DIR_OUT, default_vals=[0])

    def enable(self):
        self._release()
        if self.v2:
            from gpiod.line import Direction
            self.req = self.g.request_lines(
                self.path, consumer='tof_xshut',
                config={self.line: self.g.LineSettings(direction=Direction.INPUT)})
        else:
            self.l.request(consumer='tof_xshut', type=self.g.LINE_REQ_DIR_IN)


class Tof:
    def __init__(self, name, addr, xshut, offset, scale):
        self.name, self.addr, self.xshut = name, addr, xshut
        self.offset, self.scale = offset, scale
        self.dev = None
        self.last = float('nan')


class TofNode(Node):
    def __init__(self):
        super().__init__('tof_node')
        P = self.declare_parameter
        P('names', ['front', 'left', 'right', 'rear'])
        P('addresses', [0x30, 0x31, 0x32, 0x33])
        P('xshut_chips', ['/dev/gpiochip4'] * 4)        # PLACEHOLDERS -- set from gpioinfo
        P('xshut_lines', [-1, -1, -1, -1])              # -1 = no XSHUT, use sensor as-is at its address
        P('distance_mode', 1)       # 1 = short (<=~1.3 m, better ambient immunity), 2 = long (<=~4 m)
        P('timing_budget_ms', 50)
        P('rate', 15.0)
        P('offsets_m', [0.0] * 4)   # per-sensor calibration (README step 6)
        P('scales', [1.0] * 4)
        P('range_min', 0.04); P('range_max', 4.0)
        P('none_as', 'nan')         # 'nan' | 'inf'
        P('bus', 4)                 # Linux I2C bus the ToFs are on (I2C4 -> /dev/i2c-4)
        g = lambda n: self.get_parameter(n).value
        self.none_as = g('none_as')
        self.rmin, self.rmax = g('range_min'), g('range_max')

        import gpiod, adafruit_vl53l1x
        from adafruit_extended_bus import ExtendedI2C
        self.gpiod = gpiod
        i2c = ExtendedI2C(g('bus'))

        self.sensors = []
        for i, name in enumerate(g('names')):
            s = Tof(name, g('addresses')[i], (g('xshut_chips')[i], g('xshut_lines')[i]),
                    g('offsets_m')[i], g('scales')[i])
            self.sensors.append(s)

        # 1) everything with an XSHUT line off
        self.xs = {}
        for s in self.sensors:
            if s.xshut[1] >= 0:
                self.xs[s.name] = XShut(gpiod, s.xshut[0], s.xshut[1])
                self.xs[s.name].disable()
        time.sleep(0.05)
        # 2) bring each up. With XSHUT: release, then re-address from 0x29.
        #    Without XSHUT (-1): sensor is assumed already at its configured address.
        for s in self.sensors:
            if s.name in self.xs:
                self.xs[s.name].enable()
                time.sleep(0.05)
                dev = adafruit_vl53l1x.VL53L1X(i2c)          # at 0x29
                dev.set_address(s.addr)
            else:
                dev = adafruit_vl53l1x.VL53L1X(i2c, address=s.addr)
            dev.distance_mode = g('distance_mode')
            dev.timing_budget = g('timing_budget_ms')
            dev.start_ranging()
            s.dev = dev
            self.get_logger().info(f'tof_{s.name} at {hex(s.addr)}')

        self.pubs = {s.name: self.create_publisher(LaserScan, f'tof_{s.name}/scan', 5)
                     for s in self.sensors}
        self.create_timer(1.0 / g('rate'), self.tick)

    def tick(self):
        stamp = self.get_clock().now().to_msg()
        for s in self.sensors:
            try:
                if not s.dev.data_ready:
                    continue
                d_cm = s.dev.distance
                s.dev.clear_interrupt()
            except OSError as e:
                self.get_logger().warn(f'tof_{s.name}: {e}', throttle_duration_sec=2.0)
                continue
            if d_cm is None:
                r = float('inf') if self.none_as == 'inf' else float('nan')
            else:
                r = d_cm / 100.0 * s.scale + s.offset
                if not (self.rmin <= r <= self.rmax):
                    r = float('nan')
            m = LaserScan()
            m.header.stamp = stamp
            m.header.frame_id = f'tof_{s.name}_link'
            m.angle_min, m.angle_max, m.angle_increment = 0.0, 1e-6, 1e-6
            m.range_min, m.range_max = self.rmin, self.rmax
            m.ranges = [r, r]
            self.pubs[s.name].publish(m)


def main():
    rclpy.init()
    n = TofNode()
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    finally:
        n.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
