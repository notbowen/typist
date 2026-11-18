"""Sweep-style low-profile tray case, derived from the real PCB outline.

Cross-section (z = 0 at PCB bottom):

      wall top ─┐                     ┌─ PCB top + WALL_ABOVE_PCB
                │  ┌───── PCB ─────┐  │
   ledge ──────►└──┘               └──┘   PCB rests on a perimeter ledge
                │   cavity for sockets │
   floor  ──────┴──────────────────────┴  -(UNDER_GAP + FLOOR)

Openings for USB/TRRS come from the keep-out volumes in components.py, so the
fit check and the case can never disagree about them.
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
    under_gap: float = 2.4       # PCB bottom to floor top (hotswap sockets are 1.85)
    ledge: float = 1.6           # width of the PCB support ledge
    wall_above_pcb: float = 1.2  # wall top above PCB top
    keepout_margin: float = 0.6  # extra room around under-board parts
    corner_round: float = 1.0    # outer corner rounding


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
    cavity = unary_union(under)

    z_floor = -(p.under_gap + p.floor)
    z_top = t + p.wall_above_pcb
    case = prism(outer, z_floor, -p.under_gap)            # floor
    case += prism(outer.difference(cavity), -p.under_gap, 0)  # ledge level
    case += prism(outer.difference(pocket), 0, z_top)     # walls around PCB

    # connector openings: subtract cable keep-outs, widened a little
    for name, ko in env.keepouts.items():
        if name == "keycap_travel":
            continue
        case -= ko
    return case, {"z_floor": z_floor, "z_top": z_top, "outer_2d": outer, "pocket_2d": pocket, "cavity_2d": cavity}


def to_print_frame(part, info):
    """Move so the case bottom sits on z = 0 (print orientation)."""
    return Pos(0, 0, -info["z_floor"]) * part
