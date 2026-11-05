"""
Map file handling for hw_robot.launch.py. Plain Python (no ROS imports) so it can be tested anywhere.

Files for a map called NAME live in maps_dir:   NAME.db   RTAB-Map database (what RTAB-Map loads/updates)
                                                NAME.yaml + NAME.pgm   occupancy grid for Nav2's map_server
Scratch copies live in maps_dir/.work, replaced originals in maps_dir/backups.

Launch arguments -> behaviour (rtab:=true, the default)
  read none, write none    new map, auto name map_<date>_<time>
  read none, write B       new map B (asks before replacing an existing B; the old one goes to backups/)
  read A,    write none    "dynamic": navigate on a scratch copy of A and keep learning; copy discarded on exit
  read A,    write A       "update": scratch copy; on clean exit A is replaced (old A copied to backups/ first)
  read A,    write B       "duplicate": scratch copy of A; on clean exit saved as B; A untouched
  read A,    static:=true  "static": RTAB-Map only localizes (adds nothing); runs on a scratch copy, discarded on exit
rtab:=false: no RTAB-Map at all. Nav2 uses A.yaml/A.pgm through map_server and the robot is assumed to start at the map origin. Needs read, no write.

A new map (no read) is written straight to its final name so a crash keeps what was mapped. Everything that starts
from an existing map works on a scratch copy and only replaces the real files after a CLEAN shutdown, so a crash or
power loss cannot damage the original.
"""
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass, field

NAME_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]*$')
EXTS = ('.db', '.yaml', '.pgm')


class PlanError(Exception):
    """A user-facing problem with the requested read/write/static/rtab combination."""


@dataclass
class Plan:
    mode: str                      # new_map | dynamic | update | duplicate | static | no_rtab
    read: str = ''
    write: str = ''
    rtab: bool = True
    localization: bool = False     # RTAB-Map localization-only (Mem/IncrementalMemory false)
    delete_db: bool = False        # RTAB-Map --delete_db_on_start (fresh database)
    db_path: str = ''              # database RTAB-Map opens
    work_copy_of: str = ''         # if set: copy this .db to db_path before starting
    export_prefix: str = ''        # where map_export_node writes NAME.yaml/.pgm ('' = no export)
    map_yaml: str = ''             # rtab:=false: yaml for map_server
    finalize: str = 'none'         # none | discard | commit
    target: str = ''               # final path prefix for 'commit'
    backup_first: list = field(default_factory=list)   # prefixes moved into backups/ before starting
    summary: str = ''


def prefix(maps_dir, name):
    return os.path.join(maps_dir, name)


def _check_name(label, name):
    if name and not NAME_RE.match(name):
        raise PlanError(f"{label}:='{name}' is not a valid map name (letters, digits, _ - . only; no slashes)")


def make_plan(read, write, static, rtab, maps_dir, stamp, confirm_overwrite, copy_for_static=True):
    """Decide what to do. Touches no files. confirm_overwrite(message) -> bool may raise PlanError."""
    read, write = (read or '').strip(), (write or '').strip()
    _check_name('read', read)
    _check_name('write', write)
    work = os.path.join(maps_dir, '.work')
    have = lambda name, ext: os.path.exists(prefix(maps_dir, name) + ext)

    if not rtab:
        if static:
            raise PlanError('static:=true and rtab:=false together make no sense: rtab:=false is already '
                            'map-only. Use one or the other.')
        if not read:
            raise PlanError('rtab:=false needs read:=<map name> (the map to trust)')
        if write:
            raise PlanError('rtab:=false cannot write a map: without RTAB-Map nothing is learned. Remove write:=')
        missing = [e for e in ('.yaml', '.pgm') if not have(read, e)]
        if missing:
            raise PlanError(f"map '{read}' has no {'/'.join(missing)} in {maps_dir}. rtab:=false needs the "
                            f"exported grid (written whenever a map is saved with RTAB-Map running).")
        return Plan(mode='no_rtab', read=read, rtab=False, map_yaml=prefix(maps_dir, read) + '.yaml',
                    summary=f"NO RTAB-Map. Nav2 uses map '{read}', robot assumed to start at the map origin; nothing is learned or saved.")

    if static:
        if not read:
            raise PlanError('static:=true needs read:=<map name>')
        if write:
            raise PlanError('static:=true cannot write: the map is never changed. Remove write:=')
        if not have(read, '.db'):
            raise PlanError(f"map '{read}' not found ({prefix(maps_dir, read)}.db)")
        src = prefix(maps_dir, read) + '.db'
        if copy_for_static:
            return Plan(mode='static', read=read, localization=True, work_copy_of=src,
                        db_path=os.path.join(work, f'{read}_static.db'), finalize='discard',
                        summary=f"STATIC: localizing on a scratch copy of '{read}'; map cannot change.")
        return Plan(mode='static', read=read, localization=True, db_path=src,
                    summary=f"STATIC: localizing directly on '{read}' (copy_for_static is off).")

    if not read:
        name = write or f'map_{stamp}'
        pre = prefix(maps_dir, name)
        backup = []
        if have(name, '.db') or have(name, '.yaml') or have(name, '.pgm'):
            if not write:
                raise PlanError(f"auto-named map '{name}' already exists; try again in a second")
            if not confirm_overwrite(f"Map '{name}' already exists. Replace it (old one is kept in backups/)?"):
                raise PlanError('not overwriting; nothing started')
            backup = [pre]
        return Plan(mode='new_map', write=name, delete_db=True, db_path=pre + '.db', export_prefix=pre,
                    backup_first=backup, summary=f"NEW MAP '{name}' (saved as it is built).")

    if not have(read, '.db'):
        raise PlanError(f"map '{read}' not found ({prefix(maps_dir, read)}.db)")
    src = prefix(maps_dir, read) + '.db'
    if not write:
        return Plan(mode='dynamic', read=read, work_copy_of=src,
                    db_path=os.path.join(work, f'{read}_dynamic.db'), finalize='discard',
                    summary=f"DYNAMIC: navigating on '{read}' and learning, on a scratch copy that is NOT saved.")
    if write != read and (have(write, '.db') or have(write, '.yaml') or have(write, '.pgm')):
        if not confirm_overwrite(f"Map '{write}' already exists. Replace it with an updated copy of '{read}' "
                                 f"(old one is kept in backups/)?"):
            raise PlanError('not overwriting; nothing started')
    mode = 'update' if write == read else 'duplicate'
    what = (f"UPDATE: '{read}' is updated in place (old copy goes to backups/)." if mode == 'update'
            else f"DUPLICATE: '{read}' is copied and the updated copy is saved as '{write}'. '{read}' is untouched.")
    return Plan(mode=mode, read=read, write=write, work_copy_of=src,
                db_path=os.path.join(work, f'{write}.db'), export_prefix=os.path.join(work, write),
                finalize='commit', target=prefix(maps_dir, write),
                summary=what + ' Saved only on a clean shutdown (Ctrl+C once, wait).')


# ---------------------------------------------------------------- file operations

def _backups(maps_dir):
    return os.path.join(maps_dir, 'backups')


def backup_move(pre, maps_dir, stamp, log=print):
    """Move NAME.db/.yaml/.pgm into backups/ (used when a map is about to be replaced by a NEW one)."""
    os.makedirs(_backups(maps_dir), exist_ok=True)
    base = os.path.basename(pre)
    for e in EXTS:
        if os.path.exists(pre + e):
            dst = os.path.join(_backups(maps_dir), f'{base}_{stamp}{e}')
            shutil.move(pre + e, dst)
            log(f'[maps] old {base}{e} -> {dst}')


def prepare(plan, maps_dir, stamp, log=print):
    """Create folders, back up what a new map replaces, make the scratch copy."""
    os.makedirs(maps_dir, exist_ok=True)
    os.makedirs(os.path.join(maps_dir, '.work'), exist_ok=True)
    for pre in plan.backup_first:
        backup_move(pre, maps_dir, stamp, log)
    if plan.work_copy_of:
        stale = [plan.db_path] + ([plan.export_prefix + e for e in ('.yaml', '.pgm')] if plan.export_prefix else [])
        for p in stale:
            if os.path.exists(p):
                log(f'[maps] removing leftover scratch file from an earlier run: {p}')
                os.remove(p)
        t0 = time.time()
        shutil.copy2(plan.work_copy_of, plan.db_path)
        log(f'[maps] scratch copy made in {time.time() - t0:.1f} s: {plan.db_path}')


def db_in_use(path):
    """True while any process still has `path` open (RTAB-Map flushes the database on exit)."""
    real = os.path.realpath(path)
    try:
        pids = [p for p in os.listdir('/proc') if p.isdigit()]
    except OSError:
        return False
    for pid in pids:
        d = f'/proc/{pid}/fd'
        try:
            for fd in os.listdir(d):
                try:
                    if os.path.realpath(os.readlink(os.path.join(d, fd))) == real:
                        return True
                except OSError:
                    continue
        except OSError:
            continue
    return False


def finalize(plan, maps_dir, stamp, wait_s=20.0, log=print):
    """Run at exit (after RTAB-Map has shut down). Discards scratch files or commits them over the real map."""
    if plan.finalize == 'none':
        return
    t0 = time.time()
    while db_in_use(plan.db_path) and time.time() - t0 < wait_s:
        time.sleep(0.5)
    if db_in_use(plan.db_path):
        log(f'[maps] {plan.db_path} is still open after {wait_s:.0f} s; leaving scratch files in place, '
            f'NOT committing. Nothing was changed.')
        return
    scratch = [plan.db_path] + ([plan.export_prefix + e for e in ('.yaml', '.pgm')] if plan.export_prefix else [])
    if plan.finalize == 'discard':
        for p in scratch:
            if os.path.exists(p):
                os.remove(p)
        log('[maps] scratch copy discarded (map not saved, as requested)')
        return
    # commit: copy old files into backups/, then replace
    if not os.path.exists(plan.db_path):
        log('[maps] no scratch database found; nothing to save')
        return
    os.makedirs(_backups(maps_dir), exist_ok=True)
    base = os.path.basename(plan.target)
    for e in EXTS:
        src = (plan.db_path if e == '.db' else plan.export_prefix + e)
        dst = plan.target + e
        if not os.path.exists(src):
            continue                                   # e.g. grid never exported: keep the old yaml/pgm
        if os.path.exists(dst):
            bk = os.path.join(_backups(maps_dir), f'{base}_{stamp}{e}')
            shutil.copy2(dst, bk)
            log(f'[maps] backup: {bk}')
        os.replace(src, dst)
    log(f"[maps] saved '{base}' ({plan.mode})")


# ---------------------------------------------------------------- Nav2 map files

def write_map(prefix_path, width, height, resolution, origin_x, origin_y, origin_yaw, data):
    """Write NAME.pgm + NAME.yaml in the same format nav2 map_saver uses ('trinary': black occupied, white free,
    grey unknown). `data` is a nav_msgs/OccupancyGrid data array (row-major from the bottom-left cell, -1 unknown)."""
    import numpy as np
    g = np.asarray(data, dtype=np.int16).reshape(height, width)
    img = np.full((height, width), 205, np.uint8)       # unknown
    img[(g >= 0) & (g <= 25)] = 254                       # free  (free_thresh 0.25)
    img[g >= 65] = 0                                      # occupied (occupied_thresh 0.65)
    img = img[::-1]                                       # PGM's first row is the TOP of the map
    pgm, yml = prefix_path + '.pgm', prefix_path + '.yaml'
    tmp = pgm + '.tmp'
    with open(tmp, 'wb') as f:
        f.write(f'P5\n{width} {height}\n255\n'.encode())
        f.write(img.tobytes())
    os.replace(tmp, pgm)                                  # pgm first: the yaml never points at a missing image
    tmp = yml + '.tmp'
    with open(tmp, 'w') as f:
        f.write(f'image: {os.path.basename(pgm)}\nmode: trinary\nresolution: {resolution}\n'
                f'origin: [{origin_x}, {origin_y}, {origin_yaw}]\nnegate: 0\n'
                f'occupied_thresh: 0.65\nfree_thresh: 0.25\n')
    os.replace(tmp, yml)


def ask_confirm_factory(overwrite_flag):
    """Interactive y/N prompt for overwrite questions; refuses (rather than guesses) when there is no terminal."""
    def ask(message):
        if overwrite_flag:
            return True
        if not sys.stdin or not sys.stdin.isatty():
            raise PlanError(message + ' No terminal to ask on: run from a terminal, or pass overwrite:=true.')
        return input(message + ' [y/N]: ').strip().lower() in ('y', 'yes')
    return ask
