#!/usr/bin/env python3
"""
General ground-truth map baker: parses a Gazebo .world SDF, rasterizes every
static model's box/cylinder collision geometry into an occupancy grid.
Generalizes to any obstacles you add later (as long as they're simple
primitive collision shapes -- meshes need a bounding-box approximation, see
notes at bottom).
"""
import sys
import math
import numpy as np
from PIL import Image
from lxml import etree

RESOLUTION = 0.05
MARGIN = 0.5

def parse_pose(pose_el):
    if pose_el is None:
        return (0,0,0,0,0,0)
    vals = [float(v) for v in pose_el.text.split()]
    while len(vals) < 6:
        vals.append(0.0)
    return tuple(vals)  # x y z roll pitch yaw

def compose(parent, child):
    px, py, pz, pr, pp, pyaw = parent
    cx, cy, cz, cr, cp, cyaw = child
    cos_y, sin_y = math.cos(pyaw), math.sin(pyaw)
    wx = px + cx*cos_y - cy*sin_y
    wy = py + cx*sin_y + cy*cos_y
    return (wx, wy, pz+cz, pr+cr, pp+cp, pyaw+cyaw)

def obb_corners(x, y, yaw, sx, sy):
    hx, hy = sx/2, sy/2
    local = [(-hx,-hy), (hx,-hy), (hx,hy), (-hx,hy)]
    cos_y, sin_y = math.cos(yaw), math.sin(yaw)
    return [(x + lx*cos_y - ly*sin_y, y + lx*sin_y + ly*cos_y) for lx, ly in local]

def main(world_path, out_prefix, skip_models=('ground_plane','sun','robot','goosebot')):
    tree = etree.parse(world_path)
    root = tree.getroot()
    world = root.find('.//world')

    shapes = []  # list of (kind, x, y, yaw, sx, sy, radius)
    for model in world.findall('model'):
        name = model.get('name', '')
        if any(s in name.lower() for s in skip_models):
            continue
        model_pose = parse_pose(model.find('pose'))
        for link in model.findall('link'):
            link_pose = parse_pose(link.find('pose'))
            world_pose = compose(model_pose, link_pose)
            wx, wy, wz, wr, wp, wyaw = world_pose
            for coll in link.findall('collision'):
                geom = coll.find('geometry')
                if geom is None:
                    continue
                box = geom.find('box')
                cyl = geom.find('cylinder')
                if box is not None:
                    sx, sy, sz = [float(v) for v in box.find('size').text.split()]
                    shapes.append(('box', wx, wy, wyaw, sx, sy, None))
                elif cyl is not None:
                    r = float(cyl.find('radius').text)
                    shapes.append(('cyl', wx, wy, wyaw, None, None, r))
                # meshes: approximate with a warning -- see notes below
                elif geom.find('mesh') is not None:
                    print(f"WARNING: {name}/{link.get('name')} uses a mesh collision -- "
                          f"not rasterized, add a bounding box manually if it should block the robot")

    if not shapes:
        print("No obstacle shapes found -- check skip_models filter or world structure")
        return

    xs = [s[1] for s in shapes]; ys = [s[2] for s in shapes]
    world_min = min(min(xs), min(ys)) - MARGIN - 1.0
    world_max = max(max(xs), max(ys)) + MARGIN + 1.0
    size_m = world_max - world_min
    px = int(round(size_m / RESOLUTION))
    grid = np.full((px, px), 255, dtype=np.uint8)

    def w2p(x, y):
        col = int(round((x - world_min) / RESOLUTION))
        row = int(round((world_max - y) / RESOLUTION))
        return row, col

    for kind, x, y, yaw, sx, sy, r in shapes:
        if kind == 'box':
            corners_px = [w2p(cx, cy) for cx, cy in obb_corners(x, y, yaw, sx, sy)]
            rows = [c[0] for c in corners_px]; cols = [c[1] for c in corners_px]
            # simple filled-polygon rasterization via PIL draw
            mask_img = Image.new('L', (px, px), 0)
            from PIL import ImageDraw
            ImageDraw.Draw(mask_img).polygon([(c[1], c[0]) for c in corners_px], fill=255)
            mask = np.array(mask_img) > 0
            grid[mask] = 0
        elif kind == 'cyl':
            rr, rc = w2p(x, y)
            rad_px = int(round(r / RESOLUTION))
            yy, xx = np.ogrid[:px, :px]
            mask = (yy-rr)**2 + (xx-rc)**2 <= rad_px**2
            grid[mask] = 0

    Image.fromarray(grid, mode='L').save(f'{out_prefix}.pgm')
    with open(f'{out_prefix}.yaml', 'w') as f:
        f.write(f"image: {out_prefix.split('/')[-1]}.pgm\nresolution: {RESOLUTION}\n"
                f"origin: [{world_min}, {world_min}, 0.0]\nnegate: 0\n"
                f"occupied_thresh: 0.65\nfree_thresh: 0.25\n")
    print(f"Baked map from {len(shapes)} shapes -> {out_prefix}.pgm ({px}x{px}px)")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <world.sdf> <output_prefix>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
