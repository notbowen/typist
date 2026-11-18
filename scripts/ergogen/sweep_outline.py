"""Extract the left-half Edge.Cuts of the open-source Ferris Sweep 2.2 PCB
(github.com/davidphilipbarr/Sweep, Solderpad Hardware License 2.1) and emit it
as ergogen polygon points, relative to the left pinky-bottom key.

  .venv/bin/python scripts/ergogen/sweep_outline.py /path/to/sweepv2.kicad_pcb > /tmp/outline.yaml
  (needs shapely; paste the points into the board polygon in ergogen/config.yaml)

Changes vs the original: the panel mouse-bites on the pinky edge are replaced by
a straight edge, the controller tab is widened by TAB_GROW mm on its outer side
(XIAO pads + 0.5 mm edge clearance), and the pinky edge / inner notch are moved
out ~2 mm for the reversible hotswap pads.  Arcs are sampled every <= 3 degrees.
"""
import math
import re
import sys

PINKY_BOTTOM = (139.856, 83.382)      # left-half pinky bottom switch centre (KiCad)
TAB_X = 236.0                         # points right of this belong to the controller tab
TAB_GROW = 2.3
# Reversible Kailh hotswap: every switch has socket pads on both faces, so one set
# always faces an edge. Grow the pinky edge outward and push the inner-column notch
# right so those pads keep 0.5 mm from Edge.Cuts (blended over a few mm, no steps).
PINKY_GROW, PINKY_BLEND = 1.9, (131.6, 140.0)
NOTCH_SHIFT = 2.0
# outer thumb: whichever way its socket faces, one face's pad lands on the diagonal
# edge below the controller tab -> push that edge out (KiCad coords, after TAB_GROW)
DIAG = ((236.95 + TAB_GROW, 88.86), (226.45, 107.45))
DIAG_GROW = 2.2
ROUND = 1.0
FILL = 3.0      # radius for filling the new inner corners
X_MIN = 128.9                         # left half (in the reference panel)


def arc_points(s, m, e, step_deg=3.0):
    (x1, y1), (x2, y2), (x3, y3) = s, m, e
    d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    ux = ((x1**2 + y1**2) * (y2 - y3) + (x2**2 + y2**2) * (y3 - y1) + (x3**2 + y3**2) * (y1 - y2)) / d
    uy = ((x1**2 + y1**2) * (x3 - x2) + (x2**2 + y2**2) * (x1 - x3) + (x3**2 + y3**2) * (x2 - x1)) / d
    r = math.hypot(x1 - ux, y1 - uy)
    a1, a2, a3 = (math.atan2(y - uy, x - ux) for x, y in (s, m, e))
    def ccw(a, b):
        return (b - a) % (2 * math.pi)
    span = ccw(a1, a3)
    if ccw(a1, a2) > span:          # mid not on the ccw path -> go clockwise
        span -= 2 * math.pi
    n = max(2, int(abs(math.degrees(span)) / step_deg) + 1)
    return [(ux + r * math.cos(a1 + span * i / n), uy + r * math.sin(a1 + span * i / n)) for i in range(n + 1)]


def main(path):
    s = open(path).read()
    segs = []
    num = r'([-\d.]+)'
    for m in re.finditer(r'\(gr_(line|arc) \(start %s %s\)(?: \(mid %s %s\))? \(end %s %s\) \(layer "Edge.Cuts"\)' % ((num,) * 6), s):
        kind = m.group(1)
        v = [float(g) if g else None for g in m.groups()[1:]]
        st, md, en = (v[0], v[1]), (v[2], v[3]), (v[4], v[5])
        if min(st[0], en[0]) < X_MIN:
            continue
        if min(st[0], en[0]) < 131.4 and not (kind == "line" and abs(st[0] - en[0]) > 1):
            # pinky-side mouse bites / stubs: dropped, gaps are bridged when chaining
            if not (st[0] > 131.4 or en[0] > 131.4):
                continue
        pts = arc_points(st, md, en) if kind == "arc" else [st, en]
        segs.append(pts)
    # chain segments into a loop by nearest endpoint
    loop = segs.pop(0)
    while segs:
        tail = loop[-1]
        best = min(range(len(segs)), key=lambda i: min(math.dist(tail, segs[i][0]), math.dist(tail, segs[i][-1])))
        seg = segs.pop(best)
        if math.dist(tail, seg[-1]) < math.dist(tail, seg[0]):
            seg = seg[::-1]
        loop += seg[1:] if math.dist(tail, seg[0]) < 1e-3 else seg
    # dedupe
    out = []
    for p in loop:
        if not out or math.dist(p, out[-1]) > 0.05:
            out.append(p)
    if math.dist(out[0], out[-1]) < 0.05:
        out.pop()
    # drop the pinky-edge stubs left between x=131.2..131.6 (keep a straight edge)
    out = [p for p in out if not (p[0] < 131.45 and 41 < p[1] < 89)]
    # widen controller tab
    out = [(x + TAB_GROW, y) if x > TAB_X else (x, y) for x, y in out]
    # grow the pinky edge (full shift at the edge, fading to 0 across the corner arcs)
    def pinky(x):
        a, b = PINKY_BLEND
        return 1.0 if x <= a else max(0.0, (b - x) / (b - a))
    out = [(x - PINKY_GROW * pinky(x), y) for x, y in out]
    # push the inner-column notch (x~220, y<49.8 in KiCad coords) right
    def notch(x, y):
        if y > 49.8 or x > 224.2:
            return 0.0
        if x >= 219.5:
            return 1.0
        return max(0.0, (x - 212.0) / 7.5)     # fade along the top arc
    out = [(x + NOTCH_SHIFT * notch(x, y), y) for x, y in out]
    # push the thumb diagonal out, then round the new corners (closing + opening)
    from shapely.geometry import MultiPoint, Polygon
    (ax, ay), (bx, by) = DIAG
    L = math.hypot(bx - ax, by - ay)
    nx, ny = (by - ay) / L, -(bx - ax) / L          # right-hand normal = outward here
    if nx < 0:
        nx, ny = -nx, -ny
    quad = Polygon([(ax, ay), (bx, by), (bx + nx * DIAG_GROW, by + ny * DIAG_GROW), (ax + nx * DIAG_GROW, ay + ny * DIAG_GROW)])
    # bridge the old corner arc (tab side -> diagonal) so no notch is left behind
    rx = 238.69 + TAB_GROW
    a2 = (ax + nx * DIAG_GROW, ay + ny * DIAG_GROW)
    bridge = MultiPoint([(rx, 81.5), (rx, a2[1]), a2, (ax, ay), (ax - 2, 81.5)]).convex_hull
    poly = Polygon(out).union(quad).union(bridge)
    poly = poly.buffer(FILL, quad_segs=8).buffer(-FILL, quad_segs=8)      # fill the new inner corners
    poly = poly.buffer(-ROUND, quad_segs=8).buffer(ROUND, quad_segs=8)    # round the new outer corners
    out = list(poly.simplify(0.02).exterior.coords)[:-1]
    # ergogen frame: relative to pinky bottom, y up
    px, py = PINKY_BOTTOM
    rel = [(round(x - px, 3), round(-(y - py), 3)) for x, y in out]
    print("# generated by scripts/ergogen/sweep_outline.py - do not edit by hand")
    print(f"# {len(rel)} points, Ferris Sweep 2.2 left outline relative to matrix_pinky_bottom (y up)")
    print("points:")
    for x, y in rel:
        print(f"  - [{x}, {y}]")


if __name__ == "__main__":
    main(sys.argv[1])
