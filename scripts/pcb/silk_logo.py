"""Add a "typist" logo to both silkscreen layers of the reversible board.

  .venv/bin/python scripts/pcb/silk_logo.py DESIGN in.kicad_pcb out.kicad_pcb
      [--geom build/pcb/sweep.geom.json] [--at X Y] [--width MM]

DESIGN: ibeam  "typ|st" wordmark, the i drawn as a text cursor (JetBrains Mono ExtraBold)
        board  the 34 keys of both halves as small squares, T key filled

The logo goes on F.SilkS and, mirrored about its own centre, on B.SilkS at the same
board position, so it reads correctly on both halves (the right half is the board
flipped). It is written as filled polygons (no font needed in KiCad). Coordinates are
KiCad's (mm, y down). Also writes out.logo.json (the polygons, for previews) and
reports anything the logo touches: pads on its own face, holes, keycaps.
Needs fonttools and tools/fonts/JetBrainsMono-ExtraBold.ttf (OFL) for `ibeam`.
"""
import argparse, json, pathlib, uuid

from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

ROOT = pathlib.Path(__file__).resolve().parents[2]
FONT = ROOT / "tools/fonts/JetBrainsMono-ExtraBold.ttf"
MIN_SILK = 0.16  # mm, thinnest stroke we draw (JLCPCB minimum is 0.15)
KEYCAP = (17.5, 16.5)  # MBK cap


def glyphs(text):
    from fontTools.pens.basePen import BasePen
    from fontTools.ttLib import TTFont

    class Flat(BasePen):
        def __init__(self, gs):
            super().__init__(gs)
            self.contours, self.cur = [], []

        def _moveTo(self, p):
            self.cur = [p]

        def _lineTo(self, p):
            self.cur.append(p)

        def _curveToOne(self, a, b, c):
            p = self.cur[-1]
            for i in range(1, 11):
                t = i / 10
                u = 1 - t
                self.cur.append(tuple(u**3 * p[k] + 3 * u * u * t * a[k] + 3 * u * t * t * b[k] + t**3 * c[k]
                                      for k in (0, 1)))

        def _closePath(self):
            self.contours.append(self.cur)

    font = TTFont(FONT)
    gs, cmap = font.getGlyphSet(), font.getBestCmap()
    out = []
    for ch in text:
        pen = Flat(gs)
        gs[cmap[ord(ch)]].draw(pen)
        shape = Polygon()
        for c in pen.contours:  # even-odd: counters become holes
            shape = shape.symmetric_difference(Polygon(c).buffer(0))
        out.append(shape)
    return out


def quad(p0, p1, p2, n=12):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in (i / n for i in range(n + 1))]


def design_ibeam(_geom):
    """Same construction as the concept sheet: 48 px mono, cells 28.8 wide, baseline y=90."""
    s, parts = 0.048, []
    for g, cx in zip(glyphs("typst"), (48, 76.8, 105.6, 163.2, 192)):
        parts.append(affinity.affine_transform(g, [s, 0, 0, -s, cx - 300 * s, 90]))
    x = 134.4
    strokes = [LineString([(x, 50), (x, 98)])]
    for y0, y1 in ((44, 50), (104, 98)):
        strokes.append(LineString(quad((x - 8.4, y0), (x, y0), (x, y1)) + quad((x, y1), (x, y0), (x + 8.4, y0))[1:]))
    parts += [l.buffer(2.5) for l in strokes]
    return unary_union(parts), None


def design_board(geom):
    """Real key positions of this board, mirrored for the other half."""
    keys = [(f["x"], -f["y"], f["rot"], f["ref"]) for f in geom["footprints"] if f["name"].startswith("CHOC")]
    side, rad, gap = 12.5, 2.6, 22.0

    def cap(x, y, rot):
        sq = box(-side / 2 + rad, -side / 2 + rad, side / 2 - rad, side / 2 - rad).buffer(rad)
        return affinity.translate(affinity.rotate(sq, -rot, origin=(0, 0)), x, y)

    left = [(cap(x, y, r), ref) for x, y, r, ref in keys]
    xmax = max(c.bounds[2] for c, _ in left)
    xmin = min(c.bounds[0] for c, _ in left)
    width = 2 * (xmax - xmin) + gap
    # T on QWERTY: top key of the inner column of the left half
    inner = max(k[0] for k in keys if abs(k[2] % 180) < 1)
    t_ref = min((k for k in keys if abs(k[0] - inner) < 0.1), key=lambda k: k[1])[3]

    def build(stroke):
        parts = []
        for c, ref in left:
            ring = c.difference(c.buffer(-stroke))
            parts.append(c if ref == t_ref else ring)
            parts.append(affinity.scale(ring, -1, 1, origin=(xmax + gap / 2, 0)))
        return unary_union(parts)

    return build, width


def dehole(poly):
    """KiCad gr_poly has no holes: cut through each hole until none are left."""
    if poly.is_empty:
        return []
    if poly.geom_type != "Polygon":
        return [q for g in poly.geoms for q in dehole(g)]
    if not poly.interiors:
        return [poly] if poly.area > 1e-6 else []
    x = Polygon(poly.interiors[0]).representative_point().x
    x0, y0, x1, y1 = poly.bounds
    return dehole(poly.intersection(box(x0 - 1, y0 - 1, x, y1 + 1))) + dehole(poly.intersection(box(x, y0 - 1, x1 + 1, y1 + 1)))


def gr_poly(poly, layer):
    pts = " ".join(f"(xy {x:.4f} {y:.4f})" for x, y in poly.exterior.coords[:-1])
    return (f'\t(gr_poly\n\t\t(pts {pts})\n\t\t(stroke (width 0) (type solid))\n\t\t(fill yes)\n'
            f'\t\t(layer "{layer}")\n\t\t(uuid "{uuid.uuid4()}")\n\t)\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("design", choices=["ibeam", "board"])
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--geom", default=str(ROOT / "build/pcb/sweep.geom.json"))
    ap.add_argument("--at", nargs=2, type=float, default=[175.86, 77.2], metavar=("X", "Y"))
    ap.add_argument("--width", type=float, default=16.0)
    a = ap.parse_args()
    geom = json.load(open(a.geom))

    shape, real_width = {"ibeam": design_ibeam, "board": design_board}[a.design](geom)
    if callable(shape):  # stroke width depends on the final scale
        shape = shape(MIN_SILK / (a.width / real_width))
    x0, y0, x1, y1 = shape.bounds
    k = a.width / (x1 - x0)
    cx, cy = a.at
    front = affinity.affine_transform(shape, [k, 0, 0, k, cx - k * (x0 + x1) / 2, cy - k * (y0 + y1) / 2])
    front = front.simplify(0.004)
    back = affinity.scale(front, -1, 1, origin=(cx, cy))
    b = front.bounds
    print(f"{a.design}: {b[2] - b[0]:.2f} x {b[3] - b[1]:.2f} mm at ({cx}, {cy}), "
          f"x {b[0]:.2f}..{b[2]:.2f}, y {b[1]:.2f}..{b[3]:.2f}")

    # what does it touch?
    for name, face, layer in (("front", front, "F.Cu"), ("back", back, "B.Cu")):
        for p in geom["pads"]:
            if layer in p["layers"] and p.get("poly"):
                d = face.distance(Polygon([(x, -y) for x, y in p["poly"]]))
                if d < 0.2:
                    print(f"  WARN {name}: {d:.2f} mm to pad {p['ref']}.{p['pad']}")
        for n in geom["npth"]:
            d = face.distance(Point(n["x"], -n["y"]).buffer(n["d"] / 2))
            if d < 0.2:
                print(f"  WARN {name}: {d:.2f} mm to hole of {n['ref']}")
        for v in geom["vias"]:
            if face.distance(Point(v[0], -v[1]).buffer(v[3] / 2)) < 0.1:
                print(f"  note {name}: over via at ({v[0]:.2f}, {-v[1]:.2f})")
    near = min((front.distance(affinity.translate(affinity.rotate(
        box(-KEYCAP[0] / 2, -KEYCAP[1] / 2, KEYCAP[0] / 2, KEYCAP[1] / 2), -f["rot"], origin=(0, 0)), f["x"], -f["y"])), f["ref"])
        for f in geom["footprints"] if f["name"].startswith("CHOC"))
    print(f"  nearest keycap: {near[1]} at {near[0]:.2f} mm" + ("  (HIDDEN under the cap)" if near[0] <= 0 else ""))

    text = open(a.src).read().rstrip()
    assert text.endswith(")")
    polys = {"F.SilkS": dehole(front), "B.SilkS": dehole(back)}
    body = "".join(gr_poly(p, layer) for layer, ps in polys.items() for p in ps)
    open(a.dst, "w").write(text[:-1] + body + ")\n")
    json.dump({layer: [[[round(x, 4), round(y, 4)] for x, y in p.exterior.coords] for p in ps]
               for layer, ps in polys.items()}, open(a.dst.replace(".kicad_pcb", ".logo.json"), "w"))
    print(f"  {sum(map(len, polys.values()))} polygons -> {a.dst}")


if __name__ == "__main__":
    main()
