"""Top-down 2D overlay of a board and its case: board outline, case walls,
under-board cavity, component envelopes and keep-outs. Fast sanity check.

  .venv/bin/python scripts/cad/plot2d.py build/pcb/left.geom.json out.png
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "cad"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from shapely.geometry import MultiPolygon, Polygon  # noqa: E402

import components  # noqa: E402
from boardgeom import Board  # noqa: E402
from case import CaseParams  # noqa: E402


def draw(ax, g, **kw):
    polys = [g] if isinstance(g, Polygon) else list(getattr(g, "geoms", []))
    for p in polys:
        if p.is_empty:
            continue
        x, y = p.exterior.xy
        ax.fill(x, y, **kw)
        for i in p.interiors:
            x, y = i.xy
            ax.fill(x, y, color="white")


def main(geom, out):
    b = Board(geom)
    p = CaseParams()
    env = components.build(b)
    fig, ax = plt.subplots(figsize=(14, 11))
    outer = b.outline.buffer(p.clearance + p.wall, join_style=1)
    draw(ax, outer.difference(b.outline.buffer(p.clearance)), color="#8a8378", label="case wall")
    draw(ax, b.outline, color="#2f6b3a", alpha=0.85, label="PCB")
    if env.bottom_2d is not None:
        draw(ax, env.bottom_2d, color="#e0a030", alpha=0.8, label="under-PCB parts")
    for f in b.by_name("PG1350"):
        draw(ax, b.local_rect(f, *components.DIMS["keycap"]), facecolor="none", edgecolor="#3050c0", lw=0.8)
    for f in b.footprints:
        ax.annotate(f.ref, (f.x, f.y), ha="center", va="center", fontsize=7, color="white")
    for name, part in env.keepouts.items():
        if name == "keycap_travel":
            continue
        bb = part.bounding_box()
        ax.add_patch(plt.Rectangle((bb.min.X, bb.min.Y), bb.size.X, bb.size.Y, fill=False, ec="red", ls="--"))
        ax.annotate(name, (bb.min.X, bb.max.Y), fontsize=7, color="red")
    ax.set_aspect("equal")
    ax.grid(alpha=0.3)
    ax.set_title(f"{geom}  (blue = keycaps, orange = parts below PCB, red = cable keep-outs)")
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    print(out)


if __name__ == "__main__":
    main(*sys.argv[1:3])
