"""Approximate 3D envelopes of the parts that sit on the PCB, plus keep-out
volumes the case must never intrude into (keycap travel, cable plugs).

Everything is in the board frame (z = 0 at PCB bottom). These are *envelopes*
for clearance checking, not pretty models; tweak the dimensions in DIMS to
match the exact parts you buy.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from shapely import affinity
from shapely.geometry import MultiPoint, Point, box
from shapely.ops import unary_union

from boardgeom import Board, prism

DIMS = {
    # Kailh Choc v1 (PG1350), no plate
    "choc_housing": (13.8, 13.8, 2.2),      # w, d, h of the bottom housing above PCB
    "choc_flange": (15.0, 15.0, 0.8),       # flange on top of the bottom housing
    "choc_top": (13.8, 13.8, 2.0),          # top housing
    "choc_pin_below": 1.4,                  # posts/pins protruding below PCB bottom
    "keycap": (17.5, 16.5),                 # choc keycap footprint (MBK / LDSA-style)
    "keycap_bottomout_z": 3.0,              # keycap underside above PCB top when pressed
    "keycap_top_z": 11.0,                   # keycap top above PCB top at rest
    "hotswap_h": 1.85,                      # Kailh choc hotswap socket height (below PCB)
    "hotswap_margin": 0.6,                  # socket body beyond its pads
    "pth_pin_below": 1.8,                   # trimmed through-hole leads / solder fillets
    "sod123_h": 1.35,                       # 1N4148W body height (below PCB)
    # Seeed XIAO nRF52840, SMD-mounted flat on the top side, USB-C toward local +y (CAD)
    "xiao": (17.8, 20.95, 1.0),             # w, l, PCB thickness (incl. solder)
    "xiao_parts_h": 1.7,                    # shield can / passives above the XIAO PCB
    "xiao_usb": (8.94, 7.35, 3.26),         # USB-C receptacle w, l, h
    "xiao_usb_overhang": 1.55,              # receptacle front beyond the XIAO PCB edge
    "usb_plug": (12.5, 7.0, 25.0),          # USB-C plug overmould w, h, length (keep-out)
    # MSK12C02 side-actuated SPDT power switch (top side, tab edge)
    "pwr_body": (6.7, 2.6, 1.5),            # along edge, depth, height
    "pwr_lever": (1.5, 2.0, 1.4),           # w, protrusion beyond the body front, h
    "pwr_access": (8.0, 7.0, 3.2),          # finger notch through the wall: w, depth, h
    # JST SH 1.0 mm 2-pin SMD side entry (SM02B-SRSS-TB), bottom side
    "jst": (6.0, 4.25, 2.95),               # w, d, h
    "jst_plug_reach": 4.0,                  # mated plug + wire bend in front of the mouth
    # LiPo pouch cell, 301230 (3.0 x 12 x 30 mm, ~110 mAh) - max envelope incl. tape/PCM
    "cell": (12.5, 31.0, 3.1),              # w, l, thickness
    "cell_floor_gap": 0.05,                 # sits on the case floor
}


@dataclass
class Envelopes:
    """solids: physical parts. keepouts: volumes that must stay empty (cables,
    keycap travel). bottom_2d: 2D footprint of everything hanging below the PCB."""
    solids: dict = field(default_factory=dict)
    keepouts: dict = field(default_factory=dict)
    bottom_2d: object = None
    bottom_depth: float = 0.0
    cell_2d: object = None           # battery pocket footprint (case-side solid, see case.py)
    cell_thickness: float = 0.0
    mount_holes: list = field(default_factory=list)


def _body_centre(board: Board, ref: str):
    pts = [(p["x"], p["y"]) for p in board.pads_of(ref)]
    return MultiPoint(pts).centroid


def build(board: Board) -> Envelopes:
    D, t = DIMS, board.thickness
    env = Envelopes()
    below = []

    env.solids["pcb"] = prism(board.outline, 0, t)

    # --- key switches -----------------------------------------------------
    sw_parts, caps = [], []
    for f in board.by_name("PG1350"):
        w, d, h = D["choc_housing"]
        fw, fd, fh = D["choc_flange"]
        tw, td, th = D["choc_top"]
        sw_parts += [prism(board.local_rect(f, w, d), t, t + h),
                     prism(board.local_rect(f, fw, fd), t + h, t + h + fh),
                     prism(board.local_rect(f, tw, td), t + h + fh, t + h + fh + th)]
        caps.append(board.local_rect(f, *D["keycap"]))
        # hotswap socket = hull of its bottom-side pads, grown a bit
        bp = [p for p in board.pads_of(f.ref) if p["layers"] == ["B.Cu"] and p["poly"]]
        if bp:
            hull = unary_union([MultiPoint(p["poly"]) for p in bp]).convex_hull
            sock = hull.buffer(D["hotswap_margin"], quad_segs=3)
            below.append((sock, D["hotswap_h"]))
    holes = {f.ref for f in board.by_name("MountingHole_NPTH")}
    env.mount_holes = [(n["x"], n["y"], n["d"]) for n in board.npth if n["ref"] in holes]
    for n in board.npth:
        if n["d"] > 1.0 and n["ref"] not in holes:
            below.append((Point(n["x"], n["y"]).buffer(n["d"] / 2 + 0.2, quad_segs=4), D["choc_pin_below"]))
    if sw_parts:
        env.solids["switches"] = _union(sw_parts)
        env.keepouts["keycap_travel"] = prism(unary_union(caps), t + D["keycap_bottomout_z"], t + D["keycap_top_z"])

    # --- through-hole leads under the board -------------------------------
    for p in board.pads:
        if p["type"] == "pth":
            below.append((Point(p["x"], p["y"]).buffer(0.8, quad_segs=3), D["pth_pin_below"]))

    # --- SMD diodes on the back --------------------------------------------
    for f in board.by_name("D_SOD-123"):
        below.append((board.local_rect(f, 4.6, 2.0), D["sod123_h"]))

    # --- XIAO nRF52840 -----------------------------------------------------
    for f in board.by_name("XIAO_nRF52840_SMD"):
        w, l, pt = D["xiao"]
        uw, ul, uh = D["xiao_usb"]
        oh = D["xiao_usb_overhang"]
        # local frame here is CAD (y up) rotated: USB end is at local +y
        body = board.local_rect(f, w, l, 0, -0.025)
        parts = board.local_rect(f, w - 1.0, l - ul - 0.5, 0, -(ul + 0.5) / 2)
        usb = board.local_rect(f, uw, ul, 0, 10.45 + oh - ul / 2)
        env.solids[f"mcu_{f.ref}"] = _union([prism(body, t, t + pt),
                                              prism(parts, t + pt, t + pt + D["xiao_parts_h"]),
                                              prism(usb, t + pt, t + pt + uh)])
        pw, ph, pl = D["usb_plug"]
        front = 10.45 + oh
        plug = board.local_rect(f, pw, pl, 0, front + pl / 2)
        z = t + pt + uh / 2
        env.keepouts[f"usb_{f.ref}"] = prism(plug, z - ph / 2, z + ph / 2)

    # --- power switch -------------------------------------------------------
    for f in board.by_name("SPDT_C128955"):
        bw, bd, bh = D["pwr_body"]
        lw, lp, lh = D["pwr_lever"]
        aw, ad, ah = D["pwr_access"]
        # footprint: lever toward local +y (CAD), body front edge at +1.35
        env.solids[f"pwr_{f.ref}"] = _union([
            prism(board.local_rect(f, bw, bd, 0, 1.35 - bd / 2), t, t + bh),
            prism(board.local_rect(f, lw, lp, 0.75, 1.35 + lp / 2), t + 0.1, t + 0.1 + lh)])
        env.keepouts[f"pwr_access_{f.ref}"] = prism(board.local_rect(f, aw, ad, 0, 1.35 + ad / 2), t - 0.2, t + ah)

    # --- battery connector + cell -------------------------------------------
    for f in board.by_name("JST_SH_SM02B-SRSS-TB"):
        jw, jd, jh = D["jst"]
        # bottom-side footprint: mouth toward local +y (CAD), body centred on y=0
        env.solids[f"jst_{f.ref}"] = prism(board.local_rect(f, jw, jd, 0, 0), -jh, 0)
        r = D["jst_plug_reach"]
        env.keepouts[f"jst_plug_{f.ref}"] = prism(board.local_rect(f, jw - 1.0, r, 0, jd / 2 + r / 2), -jh, -0.2)
    env.cell_2d = None
    mcus = board.by_name("XIAO_nRF52840_SMD")
    if mcus:
        m = mcus[0]
        # cell lies under the controller tab, on the XIAO's local +x side - away from
        # its BAT+/BAT- through-holes (the XIAO is not mirrored on the right half)
        s = 1
        cw, cl, ct = D["cell"]
        top = m.y + 10.45 + D["xiao_usb_overhang"] - 0.9     # just inside the tab's top edge
        cell = box(m.x + s * 3.65 - cw / 2, top - cl, m.x + s * 3.65 + cw / 2, top)
        env.cell_2d = cell
        env.cell_thickness = ct

    env.bottom_2d = unary_union([g for g, _ in below]) if below else None
    env.bottom_depth = max((d for _, d in below), default=0.0)
    if below:
        # merge in 2D per depth: one prism per depth is far faster than hundreds of solids
        by_depth: dict[float, list] = {}
        for g, d in below:
            by_depth.setdefault(round(d, 3), []).append(g)
        env.solids["under_pcb"] = _union([prism(unary_union(gs), -d, 0) for d, gs in by_depth.items()])
    return env


def _oriented_box(cx, cy, length, width, dx, dy):
    import math
    from shapely.geometry import box
    r = box(-length / 2, -width / 2, length / 2, width / 2)
    r = affinity.rotate(r, math.degrees(math.atan2(dy, dx)), origin=(0, 0))
    return affinity.translate(r, cx, cy)


def _union(parts):
    # A compound (no boolean fuse) is much faster and fine for clearance checks.
    from build123d import Compound
    return Compound(children=list(parts))
