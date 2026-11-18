"""Approximate 3D envelopes of the parts that sit on the PCB, plus keep-out
volumes the case must never intrude into (keycap travel, cable plugs).

Everything is in the board frame (z = 0 at PCB bottom). These are *envelopes*
for clearance checking, not pretty models; tweak the dimensions in DIMS to
match the exact parts you buy.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from shapely import affinity
from shapely.geometry import MultiPoint, Point
from shapely.ops import unary_union

from boardgeom import Board, prism

DIMS = {
    # Kailh Choc v1 (PG1350), no plate
    "choc_housing": (13.8, 13.8, 2.2),      # w, d, h of the bottom housing above PCB
    "choc_flange": (15.0, 15.0, 0.8),       # flange on top of the bottom housing
    "choc_top": (13.8, 13.8, 2.0),          # top housing
    "choc_pin_below": 1.4,                  # posts/pins protruding below PCB bottom
    "keycap": (17.5, 16.5),                 # choc keycap footprint
    "keycap_bottomout_z": 3.0,              # keycap underside above PCB top when pressed
    "keycap_top_z": 11.0,                   # keycap top above PCB top at rest
    "hotswap_h": 1.85,                      # Kailh choc hotswap socket height (below PCB)
    "hotswap_margin": 0.6,                  # socket body beyond its pads
    # Pro Micro on low-profile sockets, components facing the PCB
    "mcu": (18.0, 33.5, 6.0),               # w, l, height above PCB top
    "mcu_usb_plug": (12.0, 7.5, 25.0),      # w, h, length of a USB plug + overmould
    "mcu_usb_z": 3.0,                       # plug centre above PCB top
    "pth_pin_below": 1.8,                   # trimmed through-hole leads
    # PJ-320A TRRS jack
    "trrs": (6.1, 12.2, 5.2),
    "trrs_lip": 1.5,                        # barrel protrusion beyond the board edge
    "trrs_plug_d": 8.0,                     # plug overmould diameter
    "trrs_plug_len": 20.0,
    "trrs_axis_z": 2.6,
}


@dataclass
class Envelopes:
    """solids: physical parts. keepouts: volumes that must stay empty (cables,
    keycap travel). bottom_2d: 2D footprint of everything hanging below the PCB."""
    solids: dict = field(default_factory=dict)
    keepouts: dict = field(default_factory=dict)
    bottom_2d: object = None
    bottom_depth: float = 0.0


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
    for n in board.npth:
        if n["d"] > 1.0:
            below.append((Point(n["x"], n["y"]).buffer(n["d"] / 2 + 0.2, quad_segs=4), D["choc_pin_below"]))
    if sw_parts:
        env.solids["switches"] = _union(sw_parts)
        env.keepouts["keycap_travel"] = prism(unary_union(caps), t + D["keycap_bottomout_z"], t + D["keycap_top_z"])

    # --- through-hole leads under the board -------------------------------
    for p in board.pads:
        if p["type"] == "pth":
            below.append((Point(p["x"], p["y"]).buffer(0.8, quad_segs=3), D["pth_pin_below"]))

    # --- Pro Micro ----------------------------------------------------------
    for f in board.by_name("ProMicro"):
        c = _body_centre(board, f.ref)
        w, l, h = D["mcu"]
        body = affinity.rotate(affinity.translate(
            affinity.scale(Point(0, 0).buffer(1, cap_style=3), l / 2, w / 2), c.x, c.y), f.rot, origin=c)
        env.solids[f"mcu_{f.ref}"] = prism(body, t, t + h)
        dx, dy = board.edge_direction(f, "x", (c.x, c.y))   # USB is on the long axis
        pw, ph, pl = D["mcu_usb_plug"]
        # plug starts at the end of the board body and runs outward
        start = l / 2 - 1.0
        plug = _oriented_box(c.x + dx * (start + pl / 2), c.y + dy * (start + pl / 2), pl, pw, dx, dy)
        z = t + D["mcu_usb_z"]
        env.keepouts[f"usb_{f.ref}"] = prism(plug, z - ph / 2, z + ph / 2)

    # --- TRRS jack ----------------------------------------------------------
    for f in board.by_name("TRRS-PJ-320A-dual"):
        c = _body_centre(board, f.ref)
        w, l, h = D["trrs"]
        dx, dy = board.edge_direction(f, "y", (c.x, c.y))   # jack axis = local y
        reach = board.edge_distance(c.x, c.y, dx, dy)
        lip = D["trrs_lip"]                                 # barrel sticks out past the edge
        mid = reach + lip - l / 2
        body = _oriented_box(c.x + dx * mid, c.y + dy * mid, l, w, dx, dy)
        env.solids[f"trrs_{f.ref}"] = prism(body, t, t + h)
        d, L = D["trrs_plug_d"], D["trrs_plug_len"]
        s0 = reach - 0.5          # opening starts at the board edge so the barrel lip clears too
        plug = _oriented_box(c.x + dx * (s0 + L / 2), c.y + dy * (s0 + L / 2), L, d, dx, dy)
        z = t + D["trrs_axis_z"]
        env.keepouts[f"trrs_plug_{f.ref}"] = prism(plug, z - d / 2, z + d / 2)

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
