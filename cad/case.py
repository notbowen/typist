"""Sweep-style low-profile tray case, derived from the real PCB outline.

Cross-section (z = 0 at PCB bottom):

      wall top ─┐                     ┌─ PCB top + WALL_ABOVE_PCB
                │  ┌───── PCB ─────┐  │
   ledge ──────►└──┘               └──┘   PCB rests on a perimeter ledge
                │   cavity for sockets │
   floor  ──────┴──────────────────────┴  -(UNDER_GAP + FLOOR)

Openings (USB-C plug, power-switch finger notch) come from the keep-out volumes
in components.py, so the fit check and the case can never disagree about them.

Wireless build: the LiPo cell lives in the under-PCB cavity below the controller
tab, located by a low fence on the floor and plugged into the JST-SH connector on
the PCB underside. The PCB is held by M2 screws (Sweep Bling LP hole positions)
into bosses that rise from the floor; remove them to lift the PCB and swap the cell.
"""
from __future__ import annotations

from dataclasses import dataclass

from build123d import Pos
from shapely.ops import unary_union

from boardgeom import Board, prism
from components import Envelopes


@dataclass
class CaseParams:
    wall: float = 2.0            # side wall thickness
    clearance: float = 0.4       # PCB edge to wall gap (per side)
    floor: float = 1.6           # floor thickness
    under_gap: float = 3.5       # PCB bottom to floor top (LiPo cell 3.1, sockets 1.85)
    ledge: float = 1.6           # width of the PCB support ledge
    wall_above_pcb: float = 1.2  # wall top above PCB top
    keepout_margin: float = 0.6  # extra room around under-board parts
    corner_round: float = 1.0    # outer corner rounding
    boss_d: float = 5.0          # PCB screw bosses
    pilot_d: float = 1.7         # M2 self-tapping pilot (use 3.2 for M2 heat-set inserts)
    pilot_skin: float = 0.6      # closed floor under the pilot hole
    fence_w: float = 1.4         # battery locating fence
    fence_h: float = 1.6
    fence_gap: float = 0.4       # cell to fence clearance


def build_case(board: Board, env: Envelopes, p: CaseParams = CaseParams()):
    t = board.thickness
    if env.bottom_depth > p.under_gap - 0.2:
        raise ValueError(f"under_gap {p.under_gap} too small for parts {env.bottom_depth} mm below PCB")

    outline = board.outline
    pocket = outline.buffer(p.clearance, join_style=1)
    outer = outline.buffer(p.clearance + p.wall, join_style=1)
    outer = outer.buffer(p.corner_round, join_style=1).buffer(-p.corner_round, join_style=1)

    support = outline.buffer(-p.ledge, join_style=2)
    under = [support]
    if env.bottom_2d is not None:
        under.append(env.bottom_2d.buffer(p.keepout_margin, quad_segs=3).intersection(pocket))
    if env.cell_2d is not None:      # battery bay: the cell may sit under the PCB support ledge
        under.append(env.cell_2d.buffer(p.fence_gap, join_style=2).intersection(pocket))
    cavity = unary_union(under)

    z_floor = -(p.under_gap + p.floor)
    z_top = t + p.wall_above_pcb
    case = prism(outer, z_floor, -p.under_gap)            # floor
    case += prism(outer.difference(cavity), -p.under_gap, 0)  # ledge level
    case += prism(outer.difference(pocket), 0, z_top)     # walls around PCB

    parts_2d = env.bottom_2d.buffer(p.keepout_margin, quad_segs=3) if env.bottom_2d is not None else None

    # PCB screw bosses (M2) under the mounting holes
    from shapely.geometry import Point
    bosses = [Point(x, y).buffer(p.boss_d / 2, quad_segs=8) for x, y, _ in env.mount_holes]
    if bosses:
        bz = unary_union(bosses)
        if parts_2d is not None:
            bz = bz.difference(parts_2d)
        case += prism(bz, -p.under_gap - 0.01, 0)

    # battery: locating fence around the cell, open toward the connector
    cell_solid = None
    if env.cell_2d is not None:
        z_cell = -p.under_gap + 0.05
        cell_solid = prism(env.cell_2d, z_cell, z_cell + env.cell_thickness)
        inner = env.cell_2d.buffer(p.fence_gap, join_style=2)
        ring = inner.buffer(p.fence_w, join_style=2).difference(inner)
        minx, miny, maxx, maxy = env.cell_2d.bounds
        ring = ring.difference(_box(minx + 2, miny - 3, maxx - 2, miny + 3))   # wire exit (connector end)
        ring = ring.intersection(pocket.buffer(-0.01))
        if parts_2d is not None:
            ring = ring.difference(parts_2d)
        if not ring.is_empty:
            case += prism(ring, -p.under_gap - 0.01, -p.under_gap + p.fence_h)

    # connector openings: subtract cable keep-outs, widened a little
    for name, ko in env.keepouts.items():
        if name == "keycap_travel":
            continue
        case -= ko
    for x, y, _ in env.mount_holes:
        case -= prism(Point(x, y).buffer(p.pilot_d / 2, quad_segs=8), z_floor + p.pilot_skin, 0.5)
    return case, {"z_floor": z_floor, "z_top": z_top, "outer_2d": outer, "pocket_2d": pocket,
                  "cavity_2d": cavity, "cell": cell_solid}


def _box(*b):
    from shapely.geometry import box
    return box(*b)


def to_print_frame(part, info):
    """Move so the case bottom sits on z = 0 (print orientation)."""
    return Pos(0, 0, -info["z_floor"]) * part
