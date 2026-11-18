"""Load board geometry exported by scripts/pcb/export_geometry.py and turn it
into shapely 2D shapes / build123d solids.

Frame: millimetres, x right, y up, z = 0 at the PCB *bottom* face.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from build123d import Face, Part, Pos, Wire, extrude
from shapely import affinity
from shapely.geometry import MultiPolygon, Point, Polygon, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union


@dataclass
class Footprint:
    ref: str
    name: str
    x: float
    y: float
    rot: float
    side: str
    bbox: tuple[float, float, float, float]


class Board:
    def __init__(self, path: str | Path):
        d = json.loads(Path(path).read_text())
        self.path = Path(path)
        self.thickness: float = d["thickness"]
        loops = [Polygon(l) for l in d["outline"]]
        outer = max(loops, key=lambda p: p.area)
        holes = [p for p in loops if p is not outer]
        self.outline: Polygon = outer.difference(unary_union(holes)) if holes else outer
        self.footprints = [Footprint(**{k: f[k] for k in Footprint.__annotations__}) for f in d["footprints"]]
        self.pads = d["pads"]
        self.npth = d["npth"]

    # -- queries -----------------------------------------------------------
    def by_name(self, name: str) -> list[Footprint]:
        return [f for f in self.footprints if f.name == name]

    def fp(self, ref: str) -> Footprint:
        return next(f for f in self.footprints if f.ref == ref)

    def pads_of(self, ref: str) -> list[dict]:
        return [p for p in self.pads if p["ref"] == ref]

    def local_rect(self, f: Footprint, w: float, h: float, cx: float = 0, cy: float = 0) -> Polygon:
        """w x h rectangle centred at (cx, cy) in the footprint's local frame (y up)."""
        r = box(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
        r = affinity.rotate(r, f.rot, origin=(0, 0))
        return affinity.translate(r, f.x, f.y)

    def edge_distance(self, x: float, y: float, dx: float, dy: float, step: float = 0.1) -> float:
        """Distance from (x, y) along (dx, dy) until leaving the board outline."""
        t = 0.0
        while t < 500 and self.outline.contains(Point(x + dx * t, y + dy * t)):
            t += step
        return t

    def edge_direction(self, f: Footprint, axis: str = "x", origin=None) -> tuple[float, float]:
        """World unit vector along the footprint's local +-`axis` that reaches the
        board edge soonest - i.e. the way an edge connector on that axis faces."""
        ox, oy = origin if origin is not None else (f.x, f.y)
        base = f.rot + (0 if axis == "x" else 90)
        best = None
        for ang in (base, base + 180):
            a = math.radians(ang)
            d = (math.cos(a), math.sin(a))
            t = self.edge_distance(ox, oy, *d)
            if best is None or t < best[0]:
                best = (t, d)
        return best[1]


# -- shapely -> build123d ---------------------------------------------------
def _ring(coords) -> Wire:
    pts = list(coords)[:-1]
    return Wire.make_polygon([(x, y, 0) for x, y in pts], close=True)


def to_faces(geom) -> list[Face]:
    polys = [geom] if isinstance(geom, Polygon) else list(getattr(geom, "geoms", []))
    faces = []
    for p in polys:
        if p.is_empty or p.area < 1e-6:
            continue
        p = orient(p.simplify(0.005), 1.0)
        faces.append(Face(_ring(p.exterior.coords), [_ring(i.coords) for i in p.interiors]))
    return faces


def prism(geom, z0: float, z1: float) -> Part:
    """Extrude a shapely (Multi)Polygon between heights z0 and z1."""
    # dir is explicit: a clockwise shapely ring gives a -Z face normal, and
    # extrude() would otherwise go downwards.
    parts = [Pos(0, 0, z0) * extrude(f, amount=z1 - z0, dir=(0, 0, 1)) for f in to_faces(geom)]
    if not parts:
        raise ValueError("empty geometry")
    out = parts[0]
    for p in parts[1:]:
        out = out + p
    return out


def as_multi(g) -> MultiPolygon:
    return g if isinstance(g, MultiPolygon) else MultiPolygon([g])
