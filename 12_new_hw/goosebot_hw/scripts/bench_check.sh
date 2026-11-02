#!/usr/bin/env bash
# bench_check.sh v3: status check for the Rock 5C / goosebot_hw bring-up.
#
#   bash bench_check.sh                      read-only checks (safe any time); offers to save a log at the end
#   bash bench_check.sh --log                same, but saves the log to bench_check_logs/ (next to this script) without asking
#   bash bench_check.sh --no-npu             skip the NPU checks (they run by default)
#   bash bench_check.sh --npu-model M.rknn   ... and run one real inference on the NPU
#   bash bench_check.sh --pulse              ALSO briefly spin each wheel (wheels LIFTED, kill switch in reach)
#
# Lines are tagged [ OK ] [WARN] [FAIL]; a summary is printed at the end.
# Logs are saved as <script folder>/bench_check_logs/YYYY-MM-DD_HH-MM-SS.log (date/time the run started).
# Override the folder with BENCH_LOG_DIR=/some/path
# NPU inference input shape defaults to 1,640,640,3 (uint8). Override: NPU_INPUT_SHAPE=1,320,320,3
# Not hardware-tested: --npu-model path, header pin-mux check, ToF probe.

# Declared wiring: physical pin numbers on the Rock 5C 40-pin header. Edit if you rewire.
# (each can also be overridden per run, e.g. TOF_SDA_PIN=3 TOF_SCL_PIN=5 bash bench_check.sh)
TOF_VCC_PIN=${TOF_VCC_PIN:-1};  TOF_SDA_PIN=${TOF_SDA_PIN:-23}; TOF_SCL_PIN=${TOF_SCL_PIN:-24}
IMU_VCC_PIN=${IMU_VCC_PIN:-17}; IMU_SDA_PIN=${IMU_SDA_PIN:-27}; IMU_SCL_PIN=${IMU_SCL_PIN:-28}

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REAL_USER=${SUDO_USER:-$(id -un)}
REAL_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6); REAL_HOME=${REAL_HOME:-$HOME}
RUN_STAMP=${BENCH_RUN_STAMP:-$(date +%Y-%m-%d_%H-%M-%S)}
LOG_DIR=${BENCH_LOG_DIR:-$SCRIPT_DIR/bench_check_logs}   # a folder next to this script

# ---- logging wrapper: re-run this script with stdout teed to a temp file, then offer to save it ----
if [ -z "${BENCH_CHECK_CHILD:-}" ]; then
  case " $* " in
    *" -h "*|*" --help "*) ;;
    *)
      TMPLOG=$(mktemp); trap 'rm -f "$TMPLOG"' EXIT
      BENCH_CHECK_CHILD=1 BENCH_RUN_STAMP="$RUN_STAMP" bash "$0" "$@" | tee "$TMPLOG"
      rc=${PIPESTATUS[0]}
      [ "$rc" -ne 0 ] && exit "$rc"
      ans=n
      case " $* " in
        *" --log "*) ans=y ;;
        *) if [ -t 0 ]; then printf '\nSave this report to %s/%s.log ? [y/N] ' "$LOG_DIR" "$RUN_STAMP"; read -r ans
           else echo; echo "  no terminal to ask on, so the log was NOT saved (re-run with --log to save automatically)"; fi ;;
      esac
      case "$ans" in
        y|Y|yes|YES)
          f="$LOG_DIR/$RUN_STAMP.log"
          mkdir -p "$LOG_DIR" 2>/dev/null || sudo mkdir -p "$LOG_DIR"
          if cp "$TMPLOG" "$f" 2>/dev/null || sudo cp "$TMPLOG" "$f"; then
            chmod 644 "$f" 2>/dev/null || sudo chmod 644 "$f"
            # when run via sudo, give the folder and file back to the invoking user
            [ -n "${SUDO_USER:-}" ] && chown "$SUDO_USER" "$LOG_DIR" "$f" 2>/dev/null
            echo "  saved: $f"
          else echo "  could not write $f"; exit 1; fi
          ;;
        *) echo "  log not saved" ;;
      esac
      exit 0
      ;;
  esac
fi

PULSE=0; MODEL=""; NPU=1
while [ $# -gt 0 ]; do
  case "$1" in
    --pulse) PULSE=1 ;;
    --log) ;;                       # handled by the wrapper above
    --no-npu) NPU=0 ;;
    --npu-model) MODEL="$2"; shift ;;
    -h|--help) sed -n '2,/^$/p' "$0"; exit 0 ;;
    *) echo "unknown option: $1"; exit 2 ;;
  esac
  shift
done

NOK=0; NWARN=0; NFAIL=0
ok()   { printf '  [ OK ] %s\n' "$*"; NOK=$((NOK+1)); }
warn() { printf '  [WARN] %s\n' "$*"; NWARN=$((NWARN+1)); }
bad()  { printf '  [FAIL] %s\n' "$*"; NFAIL=$((NFAIL+1)); }
info() { printf '         %s\n' "$*"; }
hdr()  { printf '\n== %s ==\n' "$*"; }
# routes "OK|msg" / "WARN|msg" / "FAIL|msg" / "INFO|msg" lines from helper python scripts
emit() {
  local l
  while IFS= read -r l; do
    case "${l%%|*}" in
      OK) ok "${l#*|}" ;; WARN) warn "${l#*|}" ;; FAIL) bad "${l#*|}" ;; *) info "${l#*|}" ;;
    esac
  done
}

# ---- Rock 5C 40-pin header knowledge (from the Radxa ROCK 5C hardware-interface docs) ----
# physical pin -> "controller role mux" for every header pin that has an I2C function
i2c_pin() {
  case "$1" in
    3) echo "8 SDA m2" ;;  5) echo "8 SCL m2" ;;
    8) echo "1 SCL m0" ;; 10) echo "1 SDA m0" ;;
    19) echo "2 SCL m4" ;; 21) echo "2 SDA m4" ;;
    23) echo "4 SDA m3" ;; 24) echo "4 SCL m3" ;;
    27) echo "6 SDA m0" ;; 28) echo "6 SCL m0" ;;
    32) echo "6 SDA m3" ;; 40) echo "6 SCL m3" ;;
    *) echo "" ;;
  esac
}
pin_gpio() {
  case "$1" in
    11) echo "GPIO4_B3: UART8_CTS/PWM15/I2S only" ;; 13) echo "GPIO4_B2: UART8_RTS/PWM14/SPI/I2S only" ;;
    *) echo "no I2C function" ;;
  esac
}
pwr_pin() { case "$1" in 1|17) echo 3V3 ;; 2|4) echo 5V ;; *) echo "" ;; esac; }
# RK3588 I2C controller base addresses (used to map /dev/i2c-N back to a real controller)
ctrl_addr() {
  case "$1" in 0) echo fd880000;; 1) echo fea90000;; 2) echo feaa0000;; 3) echo feab0000;; 4) echo feac0000;;
    5) echo fead0000;; 6) echo fec80000;; 7) echo fec90000;; 8) echo feca0000;; esac
}
bus_for_ctrl() {
  local a d; a=$(ctrl_addr "$1")
  for d in /sys/class/i2c-dev/i2c-*; do
    [ -e "$d" ] || continue
    readlink -f "$d/device" | grep -q "/$a\.i2c/" && { basename "$d" | sed 's/^i2c-//'; return; }
  done
}
# wire_check NAME VCC_PIN SDA_PIN SCL_PIN : static check of declared pins; sets NAME_CTRL / NAME_MUX when valid
wire_check() {
  local n=$1 v=$2 sda=$3 scl=$4 s c
  case "$(pwr_pin "$v")" in
    3V3) ok "$n VCC on pin $v = 3.3V" ;;
    5V)  bad "$n VCC on pin $v is 5V (sensor wants 3.3V: pins 1 or 17)" ;;
    *)   bad "$n VCC on pin $v is not a power pin" ;;
  esac
  s=$(i2c_pin "$sda"); c=$(i2c_pin "$scl")
  printf -v "${n}_CTRL" '%s' ""; printf -v "${n}_MUX" '%s' ""
  if [ -z "$s" ] || [ -z "$c" ]; then
    [ -z "$s" ] && bad "$n SDA on pin $sda cannot be I2C on the Rock 5C ($(pin_gpio "$sda"))"
    [ -z "$c" ] && bad "$n SCL on pin $scl cannot be I2C on the Rock 5C ($(pin_gpio "$scl"))"
    info "I2C-capable header pins: 3/5 (I2C8), 8/10 (I2C1), 19/21 (I2C2), 23/24 (I2C4), 27/28 (I2C6), 32/40 (I2C6 alt)"
    return
  fi
  set -- $s; local sctrl=$1 srole=$2 smux=$3
  set -- $c; local cctrl=$1 crole=$2 cmux=$3
  if [ "$srole" != SDA ] || [ "$crole" != SCL ]; then
    bad "$n SDA/SCL look swapped: pin $sda is $srole, pin $scl is $crole"
  elif [ "$sctrl" != "$cctrl" ] || [ "$smux" != "$cmux" ]; then
    bad "$n SDA pin $sda is I2C$sctrl but SCL pin $scl is I2C$cctrl (must be the same bus)"
  else
    ok "$n SDA/SCL on pins $sda/$scl = I2C$sctrl (overlay rk3588-i2c${sctrl}-${smux})"
    printf -v "${n}_CTRL" '%s' "$sctrl"; printf -v "${n}_MUX" '%s' "$smux"
  fi
}
# best-effort: confirm the pins are actually muxed to the expected I2C group (needs debugfs + root)
mux_check() {
  local n=$1 c=$2 m=$3 found
  found=$(printf '%s\n' "$PINMUX" | grep -o "i2c${c}m[0-9]" | sort -u | paste -sd' ' -)
  if [ -z "$found" ]; then warn "$n: no i2c${c} pin group is active (overlay rk3588-i2c${c}-${m} not enabled?)"
  else case " $found " in
    *" i2c${c}${m} "*) ok "$n pins are muxed as i2c${c}${m}" ;;
    *) bad "$n: i2c${c} is muxed as [$found] but the wiring needs i2c${c}${m} (wrong overlay)" ;;
  esac; fi
}

DRIVER_RUNNING=0
pgrep -f motor_driver_node >/dev/null 2>&1 && DRIVER_RUNNING=1

# ------------------------------------------------------------------
printf 'bench_check run %s on %s\n' "$RUN_STAMP" "$(hostname)"
hdr "System"
. /etc/os-release; info "$PRETTY_NAME, kernel $(uname -r), $(python3 --version 2>&1)"
[ -n "${ROS_DISTRO:-}" ] && ok "ROS_DISTRO=$ROS_DISTRO" || warn "ROS_DISTRO unset (source /opt/ros/jazzy/setup.bash and your workspace)"
mem_mb=$(free -m | awk '/Mem:/{print $2}'); avail_mb=$(free -m | awk '/Mem:/{print $7}')
info "RAM total ${mem_mb} MB, available ${avail_mb} MB"
if swapon --show --noheadings 2>/dev/null | grep -q .; then ok "swap: $(swapon --show --noheadings | awk '{print $1" "$3}' | paste -sd, -)"; else warn "no swap configured (SLAM + Nav2 + NPU on this RAM size will want some)"; fi
info "default boot target: $(systemctl get-default 2>/dev/null) (multi-user.target = headless, saves RAM)"
maxt=0; for z in /sys/class/thermal/thermal_zone*/temp; do [ -r "$z" ] && t=$(($(cat "$z")/1000)) && [ "$t" -gt "$maxt" ] && maxt=$t; done
if [ "$maxt" -ge 80 ]; then warn "hottest thermal zone ${maxt} C"; else ok "hottest thermal zone ${maxt} C"; fi
timedatectl 2>/dev/null | grep -q 'synchronized: yes' && ok "clock synchronized" || warn "clock NOT synchronized (ROS timestamps / TF will jump)"

# ------------------------------------------------------------------
hdr "Permissions"
grp=$(id -nG "$REAL_USER")
[ -n "${SUDO_USER:-}" ] && info "running under sudo: group checks are for $REAL_USER; ROS env is NOT inherited (sudo -E, or run without sudo, for the ROS checks)"
for g in i2c gpio; do case " $grp " in *" $g "*) ok "user in group $g" ;; *) bad "user NOT in group $g (usermod -aG $g \$USER, then log out/in)" ;; esac; done
unreadable=0; for c in /dev/gpiochip*; do [ -r "$c" ] && [ -w "$c" ] || unreadable=$((unreadable+1)); done
[ "$unreadable" -eq 0 ] && ok "all /dev/gpiochip* readable+writable" || bad "$unreadable gpiochip device(s) not accessible (udev rule / re-login?)"

# ------------------------------------------------------------------
hdr "ROS packages"
for p in nav2-bringup robot-localization rtabmap-ros stereo-image-proc image-proc xacro camera-calibration teleop-twist-keyboard robot-state-publisher; do
  v=$(dpkg-query -W -f='${Status} ${Version}' ros-jazzy-$p 2>/dev/null)
  case "$v" in "install ok installed"*) ok "ros-jazzy-$p ${v#install ok installed }" ;; *) bad "ros-jazzy-$p not installed" ;; esac
done

hdr "goosebot_hw workspace"
CFG=""
if command -v ros2 >/dev/null 2>&1; then
  P=$(ros2 pkg prefix goosebot_hw 2>/dev/null)
  if [ -n "$P" ]; then
    ok "goosebot_hw found at $P"
    CFG="$P/share/goosebot_hw/config/hw_params.yaml"
    exes=$(ros2 pkg executables goosebot_hw 2>/dev/null | awk '{print $2}' | paste -sd' ' -)
    for e in motor_driver_node imu_node tof_node stereo_camera_node cmd_vel_mux_node cmd_vel_to_odom; do
      case " $exes " in *" $e "*) ;; *) bad "executable missing: $e (rebuild?)" ;; esac
    done
  else
    bad "goosebot_hw not found by ros2 (build with colcon and source install/setup.bash)"
  fi
else
  bad "ros2 command not found (source ROS)"
fi
[ -f "$CFG" ] || { [ -f "$SCRIPT_DIR/config/hw_params.yaml" ] && CFG="$SCRIPT_DIR/config/hw_params.yaml"; }
[ -f "$CFG" ] || CFG=$(find "$REAL_HOME" -maxdepth 6 -name hw_params.yaml -path '*goosebot_hw*' 2>/dev/null | head -1)
if [ -f "$CFG" ]; then info "config: $(readlink -f "$CFG")"; else warn "hw_params.yaml not found"; CFG=""; fi
[ "$DRIVER_RUNNING" -eq 1 ] && info "motor_driver_node is currently RUNNING" || info "motor_driver_node is not running"

# ------------------------------------------------------------------
hdr "Header wiring (declared pins vs Rock 5C pinout)"
info "declared: ToF VCC=$TOF_VCC_PIN SDA=$TOF_SDA_PIN SCL=$TOF_SCL_PIN | IMU VCC=$IMU_VCC_PIN SDA=$IMU_SDA_PIN SCL=$IMU_SCL_PIN"
wire_check TOF "$TOF_VCC_PIN" "$TOF_SDA_PIN" "$TOF_SCL_PIN"
wire_check IMU "$IMU_VCC_PIN" "$IMU_SDA_PIN" "$IMU_SCL_PIN"
info "(static check only: it validates pin numbers, not whether wires are physically connected; the scans below do that)"
PINMUX=$(cat /sys/kernel/debug/pinctrl/*/pinmux-pins 2>/dev/null || sudo -n cat /sys/kernel/debug/pinctrl/*/pinmux-pins 2>/dev/null)
if [ -n "$PINMUX" ]; then
  [ -n "$IMU_CTRL" ] && mux_check IMU "$IMU_CTRL" "$IMU_MUX"
  [ -n "$TOF_CTRL" ] && mux_check TOF "$TOF_CTRL" "$TOF_MUX"
else
  info "pin-mux not readable (needs root + debugfs); run with sudo to confirm the overlay muxed the pins"
fi

# ------------------------------------------------------------------
hdr "I2C buses and devices"
IMU_USE=${IMU_CTRL:-6}; IMU_USEMUX=${IMU_MUX:-m0}
PCA_BUS=$(bus_for_ctrl 8); PCA_BUS=${PCA_BUS:-8}
IMU_BUS=$(bus_for_ctrl "$IMU_USE"); IMU_BUS=${IMU_BUS:-$IMU_USE}
[ -e /dev/i2c-$PCA_BUS ] && ok "/dev/i2c-$PCA_BUS exists (I2C8, header pins 3/5, PCA9685)" || bad "/dev/i2c-$PCA_BUS missing (enable overlay rk3588-i2c8-m2)"
[ -e /dev/i2c-$IMU_BUS ] && ok "/dev/i2c-$IMU_BUS exists (I2C$IMU_USE, IMU)" || bad "/dev/i2c-$IMU_BUS missing (enable overlay rk3588-i2c${IMU_USE}-${IMU_USEMUX})"
scan() { i2cdetect -y "$1" 2>/dev/null | awk 'NR>1{for(i=2;i<=NF;i++) if($i!="--") print $i}'; }
if command -v i2cdetect >/dev/null; then
  a8=$(scan "$PCA_BUS" | paste -sd' ' -); a6=$(scan "$IMU_BUS" | paste -sd' ' -)
  info "bus $PCA_BUS (I2C8) addresses: ${a8:-none}"; info "bus $IMU_BUS (I2C$IMU_USE) addresses: ${a6:-none}"
  case " $a8 " in *" 40 "*) ok "PCA9685 at 0x40" ;; *) bad "PCA9685 not found at 0x40 on bus $PCA_BUS" ;; esac
  case " $a8 " in *" 70 "*) info "0x70 = PCA9685 all-call address (not a second device)" ;; esac
  case " $a6 " in *" 68 "*|*" 69 "*) ok "IMU found on bus $IMU_BUS" ;;
    *) bad "no IMU at 0x68/0x69 on bus $IMU_BUS (check VCC pin $IMU_VCC_PIN, GND, SDA pin $IMU_SDA_PIN, SCL pin $IMU_SCL_PIN)" ;; esac
else bad "i2cdetect missing (sudo apt install i2c-tools)"; fi

emit < <(IMU_BUS="$IMU_BUS" python3 - <<'PY'
import os
try:
    from smbus2 import SMBus
    b = SMBus(int(os.environ.get("IMU_BUS", "6")))
    for a in (0x68, 0x69):
        try:
            w = b.read_byte_data(a, 0x75)
            print(f"{'OK' if w == 0x68 else 'WARN'}|MPU6050 WHO_AM_I at 0x{a:02x} = 0x{w:02x} ({'genuine MPU6050' if w == 0x68 else 'unexpected, clone or different chip?'})")
            break
        except OSError:
            pass
except Exception as e:
    print(f"INFO|IMU WHO_AM_I check skipped ({type(e).__name__})")
PY
)

# ------------------------------------------------------------------
hdr "ToF (VL53L1X) probe on the header I2C buses"
TOF_BUSES=""; for c in 1 2 4 6 8; do b=$(bus_for_ctrl "$c"); [ -n "$b" ] && TOF_BUSES="$TOF_BUSES $b"; done
TOF_EXPECT=""; [ -n "$TOF_CTRL" ] && TOF_EXPECT=$(bus_for_ctrl "$TOF_CTRL")
info "probing buses:${TOF_BUSES:- none} at 0x29 and 0x30-0x33 (reads the model-ID register)"
emit < <(TOF_BUSES="$TOF_BUSES" TOF_EXPECT="$TOF_EXPECT" TOF_SDA="$TOF_SDA_PIN" TOF_SCL="$TOF_SCL_PIN" python3 - <<'PY'
import os
def out(t, m): print(f"{t}|{m}")
try:
    from smbus2 import SMBus, i2c_msg
except Exception as e:
    out("FAIL", f"ToF probe skipped: smbus2 import failed ({type(e).__name__})"); raise SystemExit
buses = [int(x) for x in os.environ.get("TOF_BUSES", "").split()]
expect = os.environ.get("TOF_EXPECT", "")
sda, scl = os.environ.get("TOF_SDA"), os.environ.get("TOF_SCL")
found = []
for n in buses:
    try:
        b = SMBus(n)
    except OSError:
        continue
    for a in (0x29, 0x30, 0x31, 0x32, 0x33):
        try:
            w = i2c_msg.write(a, [0x01, 0x0F]); r = i2c_msg.read(a, 2)
            b.i2c_rdwr(w, r)
            found.append((n, a, list(r)))
        except OSError:
            pass
    b.close()
if not found:
    out("FAIL", f"no VL53L1X answered on buses {buses or 'none'} (check VCC, GND, and that SDA/SCL pins {sda}/{scl} are an I2C pair)")
for n, a, ident in found:
    good = ident == [0xEA, 0xCC]
    msg = f"VL53L1X model ID 0x{ident[0]:02X}{ident[1]:02X} at 0x{a:02x} on bus {n}" if good else \
          f"device at 0x{a:02x} on bus {n} answered but model ID is 0x{ident[0]:02X}{ident[1]:02X} (VL53L1X is 0xEACC; other chip?)"
    out("OK" if good else "WARN", msg)
    if good and expect and str(n) != expect:
        out("WARN", f"...but declared pins {sda}/{scl} map to bus {expect}, not bus {n}: the wiring is not what the config says")
    elif good and not expect:
        out("WARN", f"...but declared pins {sda}/{scl} are not an I2C pair, so the sensor must be wired to different pins than declared")
PY
)

# ------------------------------------------------------------------
hdr "Python modules (system python3)"
emit < <(python3 - <<'PY'
import importlib
for m in ("smbus2", "yaml", "cv2", "gpiod", "board", "busio", "adafruit_pca9685", "adafruit_vl53l1x"):
    try:
        mod = importlib.import_module(m)
        print(f"OK|{m} {getattr(mod, '__version__', '')}")
    except Exception as e:
        print(f"FAIL|{m} import failed ({type(e).__name__}: {str(e)[:80]})")
PY
)

# ------------------------------------------------------------------
hdr "GPIO chips (for ToF XSHUT pins)"
command -v gpioinfo >/dev/null && ok "gpiod tools installed" || warn "gpiodetect/gpioinfo missing (sudo apt install gpiod); needed to pick XSHUT lines"
for c in /sys/bus/gpio/devices/gpiochip*; do [ -e "$c" ] || continue; info "$(basename "$c") -> $(readlink -f "$c" | sed 's#.*/devices/##')"; done

# ------------------------------------------------------------------
hdr "Motor config (hw_params.yaml) and PCA9685 live state"
emit < <(CFG="$CFG" DRIVER_RUNNING="$DRIVER_RUNNING" PCA_BUS="$PCA_BUS" python3 - <<'PY'
import os, sys
def out(t, m): print(f"{t}|{m}")
names = {"fl": [0, 1], "rl": [2, 3], "rr": [4, 5], "fr": [6, 7]}
inv = {"left": False, "right": False}
cfg = os.environ.get("CFG", "")
if cfg:
    try:
        import yaml
        p = yaml.safe_load(open(cfg))["motor_driver"]["ros__parameters"]
        for k in names:
            if k in p: names[k] = p[k]
        inv["left"], inv["right"] = p.get("invert_left", False), p.get("invert_right", False)
        out("INFO", f"v_max={p.get('v_max')} m/s, min_duty={p.get('min_duty')}, max_duty={p.get('max_duty')}, "
                    f"wheel_separation={p.get('wheel_separation')}, invert_left={inv['left']}, invert_right={inv['right']}")
        if p.get("dry_run"): out("WARN", "dry_run is true in config (motors will not move)")
    except Exception as e:
        out("FAIL", f"could not parse motor_driver params: {e}")
allch = [c for v in names.values() for c in v]
if len(allch) != 8 or len(set(allch)) != 8 or any((not isinstance(c, int)) or c < 0 or c > 15 for c in allch):
    out("FAIL", f"PCA channel mapping invalid (need 8 distinct channels 0-15): {names}")
else:
    out("OK", "PCA channel mapping: " + ", ".join(f"{k.upper()}={v[0]}/{v[1]}" for k, v in names.items()))
try:
    from smbus2 import SMBus
    b = SMBus(int(os.environ.get("PCA_BUS", "8")))
    m1 = b.read_byte_data(0x40, 0x00); pre = b.read_byte_data(0x40, 0xFE)
    freq = 25_000_000 / (4096 * (pre + 1))
    out("INFO", f"MODE1=0x{m1:02x} ({'asleep/reset state' if m1 & 0x10 else 'awake'}), prescale={pre} (~{freq:.0f} Hz at 25 MHz osc)")
    duty = {}
    for n in range(16):
        base = 0x06 + 4 * n
        on_l, on_h, off_l, off_h = (b.read_byte_data(0x40, base + i) for i in range(4))
        if off_h & 0x10: d = 0.0
        elif on_h & 0x10: d = 1.0
        else:
            on = ((on_h & 0xF) << 8) | on_l; off = ((off_h & 0xF) << 8) | off_l
            d = ((off - on) % 4096) / 4096
        duty[n] = d
    running = os.environ.get("DRIVER_RUNNING") == "1"
    for k, (c1, c2) in names.items():
        out("INFO", f"{k.upper()}: ch{c1}={duty.get(c1, 0)*100:.0f}%  ch{c2}={duty.get(c2, 0)*100:.0f}%")
    active = [n for n, d in duty.items() if d > 0.005]
    if active and not running:
        out("FAIL", f"PCA outputs ACTIVE with no motor_driver running: channels {active}. "
                    "Chip holds its last PWM: cut power / kill switch, or run the driver and stop it.")
    elif active:
        out("INFO", f"outputs active (driver running): channels {active}")
    else:
        out("OK", "all PCA9685 outputs idle (0%)")
except Exception as e:
    out("FAIL", f"cannot read PCA9685 registers on bus {os.environ.get('PCA_BUS', '8')}: {type(e).__name__}: {e}")
# other sections in the config that are still placeholders
if cfg:
    try:
        y = yaml.safe_load(open(cfg))
        s = y.get("stereo_camera", {}).get("ros__parameters", {})
        if "CHANGE_ME" in str(s.get("left_device", "")) + str(s.get("right_device", "")):
            out("INFO", "stereo device paths still CHANGE_ME (expected until the camera mount is done)")
        t = y.get("tof_node", {}).get("ros__parameters", {})
        if all(v < 0 for v in t.get("xshut_lines", [-1])):
            out("INFO", "ToF xshut_lines all -1 (disabled; set them when ToFs are wired)")
    except Exception:
        pass
PY
)

# ------------------------------------------------------------------
hdr "Cameras"
n=$(ls /dev/v4l/by-path/ 2>/dev/null | grep -c 'video-index0')
if [ "$n" -ge 2 ]; then ok "$n camera device(s) by-path"; elif [ "$n" -eq 1 ]; then warn "only 1 camera device (stereo needs 2)"; else warn "no cameras detected (check connection?)"; fi
ls -l /dev/v4l/by-path/ 2>/dev/null | grep -i 'video-index0' | awk '{print "         "$9" -> "$11}'
command -v v4l2-ctl >/dev/null && v4l2-ctl --list-devices 2>/dev/null | sed 's/^/         /' || info "v4l2-ctl not installed (sudo apt install v4l-utils)"
[ "$n" -ge 2 ] && command -v lsusb >/dev/null && info "check the two cameras are on different USB controllers: lsusb -t"

# ------------------------------------------------------------------
if [ "$NPU" -eq 1 ] || [ -n "$MODEL" ]; then
hdr "NPU"
klog=$(journalctl -k -b --no-pager 2>/dev/null | grep -i rknpu; true)
[ -z "$klog" ] && klog=$(dmesg 2>/dev/null | grep -i rknpu; true)
if echo "$klog" | grep -qi 'Initialized rknpu'; then ok "driver: $(echo "$klog" | grep -i 'Initialized rknpu' | sed 's/.*Initialized/Initialized/' | head -1)"; else
  [ -z "$klog" ] && warn "cannot read kernel log or no rknpu lines (try: sudo dmesg | grep -i rknpu)" || bad "rknpu lines present but no 'Initialized rknpu'"; fi
for d in /sys/class/devfreq/*npu*; do [ -d "$d" ] && info "$(basename "$d") cur_freq=$(cat "$d/cur_freq" 2>/dev/null) Hz"; done
if python3 -c 'from rknnlite.api import RKNNLite' 2>/dev/null; then
  rv=$(python3 -c 'import importlib.metadata as m
try: print(m.version("rknn-toolkit-lite2"))
except Exception: print("version unknown")' 2>/dev/null)
  ok "rknnlite importable (rknn-toolkit-lite2 $rv)"
  if [ -e /usr/lib/librknnrt.so ] || ldconfig -p 2>/dev/null | grep -qi librknnrt; then
    ok "librknnrt.so present: $(ls -l /usr/lib/librknnrt.so 2>/dev/null | awk '{print $5" bytes"}')"
    info "runtime: $(strings /usr/lib/librknnrt.so 2>/dev/null | grep -m1 -i 'librknnrt version' || echo 'version string not found')"
  else
    warn "no librknnrt.so in /usr/lib: rknnlite needs it (the pip wheel is ~0.5 MB and does not contain it)"
  fi
else
  warn "rknnlite not importable (pip install rknn-toolkit-lite2, see notes)"
  ldconfig -p 2>/dev/null | grep -qi librknnrt && info "system librknnrt.so present" || info "no system librknnrt.so either"
fi
if [ -n "$MODEL" ]; then
  info "running inference test on $MODEL (loads the model, 5 runs)"
  emit < <(MODEL="$MODEL" python3 - <<'PY'
import os, time
def out(t, m): print(f"{t}|{m}")
try:
    import numpy as np
    from rknnlite.api import RKNNLite
    shape = tuple(int(x) for x in os.environ.get("NPU_INPUT_SHAPE", "1,640,640,3").split(","))
    r = RKNNLite()
    if r.load_rknn(os.environ["MODEL"]) != 0: raise RuntimeError("load_rknn failed")
    if r.init_runtime() != 0: raise RuntimeError("init_runtime failed (driver/runtime version mismatch?)")
    x = np.zeros(shape, dtype=np.uint8)
    r.inference(inputs=[x])
    t0 = time.time()
    for _ in range(5): res = r.inference(inputs=[x])
    ms = (time.time() - t0) / 5 * 1000
    out("OK", f"NPU inference works: {ms:.0f} ms/run, outputs {[tuple(o.shape) for o in res]}")
    r.release()
except Exception as e:
    out("FAIL", f"NPU inference test failed: {type(e).__name__}: {e} (wrong NPU_INPUT_SHAPE? set it to your model's input)")
PY
)
else
  info "NPU inference not tested. Run: bash bench_check.sh --npu-model /path/to/model.rknn"
fi

else
  hdr "NPU"; info "skipped (--no-npu given)"
fi

# ------------------------------------------------------------------
hdr "Running ROS nodes (only meaningful if you launched something)"
if command -v ros2 >/dev/null 2>&1; then
  nodes=$(timeout 8 ros2 node list 2>/dev/null)
  if [ -z "$nodes" ]; then info "no ROS nodes running"; else
    for n in motor_driver cmd_vel_mux imu_node tof_node stereo_camera ekf_filter_node cmd_vel_to_odom; do
      echo "$nodes" | grep -q "/$n\$" && info "running: /$n" || info "not running: /$n"
    done
  fi
fi

# ------------------------------------------------------------------
if [ "$PULSE" -eq 1 ]; then
  hdr "Wheel pulse test (ACTIVE)"
  if [ "$DRIVER_RUNNING" -eq 1 ]; then bad "motor_driver_node is running; stop it first"
  elif [ -z "$CFG" ]; then bad "no hw_params.yaml found"
  else
    echo "  This spins each wheel forward briefly at low duty, one at a time."
    echo "  Wheels must be OFF THE GROUND and your hand on the kill switch."
    printf '  Type LIFTED to continue: '; read -r ans
    if [ "$ans" = "LIFTED" ]; then
      emit < <(CFG="$CFG" python3 - <<'PY'
import os, time, yaml
def out(t, m): print(f"{t}|{m}", flush=True)
p = yaml.safe_load(open(os.environ["CFG"]))["motor_driver"]["ros__parameters"]
duty = float(os.environ.get("PULSE_DUTY", "0.35"))
chans = {k: p.get(k, d) for k, d in (("fl", [0, 1]), ("rl", [2, 3]), ("rr", [4, 5]), ("fr", [6, 7]))}
inv = {"fl": p.get("invert_left", False), "rl": p.get("invert_left", False),
       "fr": p.get("invert_right", False), "rr": p.get("invert_right", False)}
import board, busio
from adafruit_pca9685 import PCA9685
pca = PCA9685(busio.I2C(board.SCL, board.SDA)); pca.frequency = p.get("pwm_frequency", 100)
try:
    for name in ("fl", "fr", "rl", "rr"):
        in1, in2 = chans[name]
        fwd = in2 if inv[name] else in1          # same rule as motor_driver_node
        out("INFO", f"{name.upper()}: forward pulse on channel {fwd} at {duty*100:.0f}% for 0.6 s ... which wheel moved, and which way?")
        pca.channels[fwd].duty_cycle = int(duty * 65535)
        time.sleep(0.6)
        pca.channels[fwd].duty_cycle = 0
        time.sleep(1.2)
    out("OK", "pulse sequence finished; compare each wheel/direction to the label above")
finally:
    for n in range(16): pca.channels[n].duty_cycle = 0
    pca.deinit()
PY
)
    else info "cancelled"; fi
  fi
fi

# ------------------------------------------------------------------
printf '\n== Summary: %d OK, %d WARN, %d FAIL ==\n' "$NOK" "$NWARN" "$NFAIL"
