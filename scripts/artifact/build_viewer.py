"""Bundle the real design outputs into one self-contained interactive HTML viewer.

  .venv/bin/python scripts/artifact/build_viewer.py build/artifact/sweep-xiao.html

Reads build/pcb/sweep.geom.json and build/pcb/sweep-drc.json (`make pcb`).
One reversible board: the left half is the board as-is, the right half is the same
board flipped over. This script turns the footprints into a parts list in board
coordinates (CAD frame, mm, y up) and places the rubber feet; the page
(scripts/artifact/viewer_template.html) builds both halves procedurally in three.js.
"""
import json
import math
import sys
from pathlib import Path

from shapely import affinity
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[2]
BOARD = "sweep"

# Part envelopes (mm). Approximate bodies for display and foot placement, not CAD models.
DIMS = {
    "socket_box": (5.0, 4.6, 1.85),      # Kailh Choc hotswap: two offset boxes per socket, h below PCB
    "sod123": (2.7, 1.6, 1.15),           # 1N4148W body
    "xiao": (17.8, 20.95, 1.0),           # XIAO nRF52840 PCB w, l, t (USB end toward +y)
    "xiao_can": 1.7,                      # shield can / passives above its PCB
    "xiao_usb": (8.94, 7.35, 3.26),       # USB-C receptacle w, l, h
    "xiao_usb_overhang": 1.55,            # receptacle front beyond the XIAO PCB edge
    "pwr_body": (6.7, 2.6, 1.5),          # MSK12C02 along edge, depth, height
    "pwr_lever": (1.5, 2.0, 1.4),
    "jst": (4.0, 4.25, 2.95),             # SM02B-SRSS-TB w, d, h; mouth toward +y
    "jst_plug_reach": 4.0,                # mated plug + wire bend in front of the mouth
    "cell": (12.0, 30.0, 3.0),            # 301230 LiPo (nominal), w, l, t
    "cell_tape": 1.0,                     # Kapton + foam tape between cell and PCB
    "led": (2.0, 1.25, 0.8),              # 0805
    "foot": (10.0, 6.0),                  # adhesive rubber foot diameter, height
    "standoff": (4.0, 3.0),               # M2 hex standoff across flats, length
    "bumpon": (7.9, 2.8),                 # 3M SJ5076 diameter, height (on the standoff end)
}
N_PAD_FEET = 3


def load(name):
    return json.loads((ROOT / f"build/pcb/{name}").read_text())


def rot(x, y, deg):
    a = math.radians(deg)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


def obox(cx, cy, w, h, deg):
    return affinity.rotate(box(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), deg, origin=(cx, cy))


def socket_boxes(fp, pads):
    """Two offset boxes (stepped Kailh socket body) from the socket's two SMD pads on one face.
    Returns [cx, cy, w, h, rot] in board coordinates."""
    p = {q["pad"]: q for q in pads}
    if "1" not in p or "2" not in p:
        return []
    l1 = rot(p["1"]["x"] - fp["x"], p["1"]["y"] - fp["y"], -fp["rot"])
    l2 = rot(p["2"]["x"] - fp["x"], p["2"]["y"] - fp["y"], -fp["rot"])
    u = 1 if l2[0] > l1[0] else -1
    w, h, _ = DIMS["socket_box"]
    out = []
    for (lx, ly), s in ((l1, 1), (l2, -1)):
        cx = lx + u * s * (0.6 + w / 2)
        gx, gy = rot(cx, ly, fp["rot"])
        out.append([round(fp["x"] + gx, 3), round(fp["y"] + gy, 3), w, h, fp["rot"]])
    return out


def zone_rings(zones):
    """Filled pours per copper layer as [[outer, hole, ...], ...], simplified to 0.02 mm so the
    viewer can draw the copper that shows through the clear solder mask."""
    out = {}
    for z in zones:
        for rings in z["polys"]:
            poly = Polygon(rings[0], rings[1:]).simplify(0.02, preserve_topology=True)
            for pg in getattr(poly, "geoms", [poly]):
                if pg.is_empty:
                    continue
                r = lambda c: [[round(x, 2), round(y, 2)] for x, y in c.coords[:-1]]
                out.setdefault(z["layer"], []).append([r(pg.exterior)] + [r(h) for h in pg.interiors])
    return out


def main(out: str):
    g, drc = load(f"{BOARD}.geom.json"), load(f"{BOARD}-drc.json")
    fps = g["footprints"]
    pads_of = {}
    for p in g["pads"]:
        pads_of.setdefault(p["ref"], []).append(p)
    one = lambda name: next(f for f in fps if f["name"] == name)

    keys = []
    for f in fps:
        if f["name"] != "CHOC_V1_HOTSWAP_REV":
            continue
        smd = [p for p in pads_of[f["ref"]] if p["type"] == "smd"]
        keys.append({"ref": f["ref"], "x": f["x"], "y": f["y"], "r": f["rot"],
                     "sock": {s: socket_boxes(f, [p for p in smd if p["layers"] == [f"{s}.Cu"]]) for s in "FB"}})
    diodes = []
    for f in fps:
        if f["name"] == "D_SOD-123":
            k = next(p for p in pads_of[f["ref"]] if p["pad"] == "1")   # pad 1 = cathode (to the row)
            diodes.append({"x": f["x"], "y": f["y"], "r": f["rot"], "k": [k["x"], k["y"]]})

    xiao = one("XIAO_nRF52840_SMD_REV")
    pwr = one("MSK12C02_REV")
    lever = rot(0, 1, pwr["rot"])                                   # lever toward local +y (CAD)
    jst = one("JST_SH_SM02B-SRSS-TB")
    mouth = rot(0, 1, jst["rot"])                                   # cable enters from local +y (CAD)
    led_gpio = {"LED1": "D6", "LED2": "D7", "LED3": "P0.09 (NFC1)", "LED4": "P0.10 (NFC2)"}
    leds = sorted(({"ref": f["ref"], "x": f["x"], "y": f["y"], "r": f["rot"], "gpio": led_gpio.get(f["ref"], "?")}
                   for f in fps if f["name"].startswith("LED_0805")), key=lambda d: d["ref"])
    holes_m2 = [[f["x"], f["y"]] for f in fps if f["name"] == "MountingHole_NPTH"]

    # LiPo under the controller tab (socket face), long side along y, ending just inside the
    # tab's top edge; its leads come out at the bottom end, toward the JST mouth.
    cw, cl, ct = DIMS["cell"]
    top = xiao["y"] + DIMS["xiao"][1] / 2 + DIMS["xiao_usb_overhang"] - 1.5
    cx = xiao["x"] + 2.5
    cell = [round(cx - cw / 2, 3), round(top - cl, 3), round(cx + cw / 2, 3), round(top, 3)]

    # ---- feet. The bottom (socket) face has no 10 mm spot clear of sockets/posts on the upper
    # half of the board, so: an M2 standoff + small bumpon at each of the 3 mounting holes
    # (they sit between switches; the screw head clears the switch flanges on top), plus
    # adhesive rubber feet on the bare board near the tab and thumbs, clear of everything that
    # sticks out on either face, so the same spots work on both halves.
    outline = Polygon(g["outline"][0])
    fd, _ = DIMS["foot"]
    posts = [h for h in g["npth"] if not 2.5 < h["d"] < 3.2]       # switch centre/side posts poke
    keep = [Point(h["x"], h["y"]).buffer(h["d"] / 2 + 0.4) for h in posts]  # through; the empty
    keep += [Point(p["x"], p["y"]).buffer(0.8) for p in g["pads"] if p["type"] == "pth"]  # 3 mm holes don't
    keep += [obox(*b[:4], b[4]).buffer(0.4) for k in keys for s in "FB" for b in k["sock"][s]]
    keep += [obox(d["x"], d["y"], 4.6, 2.2, d["r"]).buffer(0.3) for d in diodes]
    jw, jd, _ = DIMS["jst"]
    r = DIMS["jst_plug_reach"]
    keep.append(obox(jst["x"] + mouth[0] * r / 2, jst["y"] + mouth[1] * r / 2, jw + 1, jd + r + 1, jst["rot"]))
    keep.append(box(*cell).buffer(1.0))
    keep += [Point(*h).buffer(4.5) for h in holes_m2]
    free = outline.buffer(-(fd / 2 + 0.6)).difference(unary_union(keep).buffer(fd / 2))
    xmin, ymin, xmax, ymax = outline.bounds
    cand = [(x / 2, y / 2) for x in range(int(xmin * 2), int(xmax * 2) + 1)
            for y in range(int(ymin * 2), int(ymax * 2) + 1) if free.contains(Point(x / 2, y / 2))]
    c = outline.centroid
    feet = [list(h) for h in holes_m2]
    pads_feet = []
    while cand and len(pads_feet) < N_PAD_FEET:
        q = max(cand, key=lambda q: min(math.hypot(q[0] - f[0], q[1] - f[1]) for f in feet + pads_feet))
        pads_feet.append(list(q))
    hull = Polygon(feet + pads_feet).convex_hull
    stable = bool(hull.buffer(-5).contains(c))

    viol = drc.get("violations", [])
    warn_types = {}
    for v in viol:
        if v.get("severity") == "warning":
            warn_types[v["type"]] = warn_types.get(v["type"], 0) + 1
    data = {
        "board": {"outline": g["outline"][0], "thickness": g["thickness"],
                  "size": [round(xmax - xmin, 1), round(ymax - ymin, 1)], "centroid": [c.x, c.y],
                  "pads": [{"l": p["layers"], "p": [[round(x, 3), round(y, 3)] for x, y in p["poly"]],
                            "ref": p["ref"], "pad": p["pad"], "net": p["net"], "x": p["x"], "y": p["y"]}
                           for p in g["pads"] if p["poly"]],
                  "holes": [[h["x"], h["y"], h["d"]] for h in g["npth"]],
                  "pth": [[p["x"], p["y"]] for p in g["pads"] if p["type"] == "pth"],
                  "tracks": g.get("tracks", []), "vias": g.get("vias", []),
                  "zones": zone_rings(g.get("zones", []))},
        "keys": keys, "diodes": diodes,
        "xiao": {k: xiao[k] for k in ("x", "y", "rot")},
        "pwr": {"x": pwr["x"], "y": pwr["y"], "rot": pwr["rot"], "lever": [round(v, 6) for v in lever]},
        "jst": {"x": jst["x"], "y": jst["y"], "rot": jst["rot"], "mouth": list(mouth)},
        "leds": leds, "holes_m2": holes_m2, "cell": cell,
        "feet": {"standoffs": feet, "pads": pads_feet, "stable": stable},
        "dims": DIMS,
        "drc": {"errors": sum(1 for v in viol if v.get("severity") == "error"),
                "warnings": sum(warn_types.values()), "warn_types": warn_types,
                "unconnected": len(drc.get("unconnected_items", [])),
                "date": drc.get("date", ""), "kicad": drc.get("kicad_version", "")},
        "stats": {"tracks": len(g.get("tracks", [])), "vias": len(g.get("vias", [])),
                  "footprints": len(fps)},
    }
    tpl = (ROOT / "scripts/artifact/viewer_template.html").read_text()
    html = tpl.replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":")))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(html)
    print(f"{out}: {len(html) / 1e6:.2f} MB; adhesive feet at {pads_feet}"
          f" ({'stable' if stable else 'CHECK: board centroid near/outside the feet'})")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "build/artifact/sweep-xiao.html"))
