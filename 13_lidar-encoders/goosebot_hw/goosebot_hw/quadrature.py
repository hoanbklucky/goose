"""
Quadrature decoding of hall wheel encoders read through libgpiod edge events (no ROS in here, so
scripts/encoder_check.py can use it without a running robot).

How it works: every edge on every A/B line is a kernel event with a timestamp. A background thread reads the events,
sorts them by timestamp (needed for libgpiod v1, which reads each line separately), and runs each encoder's 2-bit
state (A<<1 | B) through the standard x4 transition table: one count per edge, sign from the order of A and B.
An edge that reports the level the line ALREADY has means the opposite edge before it was lost (kernel event buffer
overflow when the CPU falls behind, or electrical noise). It is counted as an ERROR and does not change the count, so
a few errors cost a few counts (under-reading), never a wrong direction.

Supports libgpiod v1 (chip.get_lines / event_read_multiple) and v2 (request_lines / read_edge_events), detected at
runtime like tof_node. The v2 path is the main one; the v1 calls follow the v1.5/1.6 Python bindings and are less
certain (not checked on this board).
"""
import threading
import time

# index = prev_state << 2 | new_state ; value = count delta, None = illegal (both bits changed)
_X = None
QDEC = [0, -1, 1, _X,
        1, 0, _X, -1,
        -1, _X, 0, 1,
        _X, 1, -1, 0]


class Quad:
    """One encoder: A and B line offsets, running count, error count."""
    def __init__(self, name, a, b):
        self.name, self.a, self.b = name, a, b
        self.state = 0
        self.count = 0
        self.errors = 0
        self.edges = 0

    def set_initial(self, va, vb):
        self.state = (int(va) << 1) | int(vb)

    def edge(self, line, level):
        """Apply one edge (line offset, new level 0/1)."""
        if line == self.a:
            new = (int(level) << 1) | (self.state & 1)
        else:
            new = (self.state & 2) | int(level)
        self.edges += 1
        if new == self.state:          # same level again: the opposite edge was missed
            self.errors += 1
            return
        d = QDEC[(self.state << 2) | new]
        if d is None:                  # cannot happen with one line per edge; kept for safety
            self.errors += 1
        else:
            self.count += d
        self.state = new


class Encoders:
    """Reads all encoders on one gpiochip in a background thread.
    encoders: dict name -> (line_a, line_b). snapshot() returns {name: (count, errors, edges)}."""

    def __init__(self, chip, encoders, consumer='goosebot_enc'):
        import gpiod
        self.gpiod = gpiod
        self.v2 = hasattr(gpiod, 'request_lines')
        self.quads = {n: Quad(n, a, b) for n, (a, b) in encoders.items()}
        self.by_line = {}
        for q in self.quads.values():
            self.by_line[q.a] = q
            self.by_line[q.b] = q
        self.lines = sorted(self.by_line)
        if len(self.lines) != 2 * len(self.quads):
            raise ValueError(f'encoder lines must all be different: {encoders}')
        self.chip_path = chip
        self.lock = threading.Lock()
        self.running = True
        self.error = None
        self._open(consumer)
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    # ---------- libgpiod setup ----------
    def _open(self, consumer):
        g = self.gpiod
        if self.v2:
            from gpiod.line import Edge
            self.req = g.request_lines(
                self.chip_path, consumer=consumer,
                config={tuple(self.lines): g.LineSettings(edge_detection=Edge.BOTH)})
            vals = self.req.get_values(self.lines)
            levels = {ln: 1 if int(v.value if hasattr(v, 'value') else v) else 0 for ln, v in zip(self.lines, vals)}
        else:
            self.chip = g.Chip(self.chip_path)
            self.bulk = self.chip.get_lines(self.lines)
            self.bulk.request(consumer=consumer, type=g.LINE_REQ_EV_BOTH_EDGES)
            levels = dict(zip(self.lines, self.bulk.get_values()))
        for q in self.quads.values():
            q.set_initial(levels[q.a], levels[q.b])

    def _read_v2(self):
        if not self.req.wait_edge_events(0.2):
            return []
        out = []
        rising = self.gpiod.EdgeEvent.Type.RISING_EDGE
        for ev in self.req.read_edge_events():
            out.append((ev.timestamp_ns, ev.line_offset, 1 if ev.event_type == rising else 0))
        return out

    def _read_v1(self):
        ready = self.bulk.event_wait(sec=0, nsec=200_000_000)
        if not ready:
            return []
        out = []
        rising = self.gpiod.LineEvent.RISING_EDGE
        for line in ready:
            for ev in line.event_read_multiple():
                out.append((ev.sec * 1_000_000_000 + ev.nsec, line.offset(), 1 if ev.type == rising else 0))
        return out

    def _run(self):
        read = self._read_v2 if self.v2 else self._read_v1
        try:
            while self.running:
                evs = read()
                if not evs:
                    continue
                evs.sort()
                with self.lock:
                    for _, line, level in evs:
                        q = self.by_line.get(line)
                        if q is not None:
                            q.edge(line, level)
        except Exception as e:          # reported by the owner through .error
            self.error = e

    # ---------- public ----------
    def snapshot(self):
        with self.lock:
            return {n: (q.count, q.errors, q.edges) for n, q in self.quads.items()}

    def zero(self):
        with self.lock:
            for q in self.quads.values():
                q.count = q.errors = q.edges = 0

    def close(self):
        self.running = False
        self.thread.join(timeout=1.0)
        try:
            if self.v2:
                self.req.release()
            else:
                self.bulk.release()
        except Exception:
            pass


def _selftest():
    """Offline check of the decoder (python3 -m goosebot_hw.quadrature)."""
    seq = [(0, 1), (1, 1), (1, 0), (0, 0)]       # (A, B) levels in one rotation direction

    def drive(q, steps):
        for a, b in steps:
            if a != (q.state >> 1):
                q.edge(q.a, a)
            if b != (q.state & 1):
                q.edge(q.b, b)

    q = Quad('t', 1, 2)
    q.set_initial(0, 0)
    drive(q, seq * 10)
    up = q.count
    drive(q, list(reversed(seq)) * 10 + [(0, 0)])   # end where it started
    print(f'10 cycles one way: {up:+d} counts (expect +/-40); back again: {q.count:+d} (expect 0); errors {q.errors}')
    q.edge(q.b, q.state & 1)                     # an edge to the level B already has = a missed edge
    print(f'missed-edge errors: {q.errors} (expect 1)')
    return up, q.count, q.errors


if __name__ == '__main__':
    _selftest()
