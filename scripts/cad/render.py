"""Headless shaded renders of STL/STEP-derived meshes (VTK via OSMesa, no GPU or
display needed). Produces one PNG with a grid of views.

  .venv/bin/python scripts/cad/render.py out.png part.stl[:color[:opacity]] ...
      [--views iso,top,front,under] [--size 1600]

Colors are names or hex, e.g.  case.stl:#c9c2b8  pcb.stl:green:0.9
Views: iso, top, front, side, under, back.
"""
import argparse
import os
import sys

os.environ.setdefault("VTK_DEFAULT_OPENGL_WINDOW", "vtkOSOpenGLRenderWindow")

import pyvista as pv  # noqa: E402

pv.OFF_SCREEN = True

# camera direction (from focal point towards camera), view-up
VIEWS = {
    "iso": ((1, -1.4, 1.3), (0, 0, 1)),
    "top": ((0, 0, 1), (0, 1, 0)),
    "front": ((0, -1, 0.0001), (0, 0, 1)),
    "side": ((1, 0, 0.0001), (0, 0, 1)),
    "back": ((-1, 1.4, 1.0), (0, 0, 1)),
    "under": ((0.8, -1.2, -1.3), (0, 0, 1)),
}


def parse(spec):
    parts = spec.split(":")
    color = parts[1] if len(parts) > 1 and parts[1] else "#b0b8c8"
    opacity = float(parts[2]) if len(parts) > 2 else 1.0
    return parts[0], color, opacity


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("meshes", nargs="+")
    ap.add_argument("--views", default="iso,top,front,under")
    ap.add_argument("--size", type=int, default=1600)
    a = ap.parse_args()

    views = a.views.split(",")
    cols = min(len(views), 2)
    rows = (len(views) + cols - 1) // cols
    w = a.size
    h = int(a.size / cols * rows * 0.7)
    p = pv.Plotter(off_screen=True, shape=(rows, cols), window_size=(w, h), border=False)
    meshes = [(pv.read(f), c, o) for f, c, o in map(parse, a.meshes)]
    for i, v in enumerate(views):
        p.subplot(i // cols, i % cols)
        p.set_background("white")
        for m, c, o in meshes:
            p.add_mesh(m, color=c, opacity=o, smooth_shading=False, specular=0.2,
                       show_edges=False, feature_angle=30)
        p.add_text(v, font_size=10, color="black")
        d, up = VIEWS[v]
        p.camera_position = "xy"
        p.camera.parallel_projection = True
        c = p.bounds_center if hasattr(p, "bounds_center") else p.center
        p.camera.focal_point = c
        p.camera.position = (c[0] + d[0] * 500, c[1] + d[1] * 500, c[2] + d[2] * 500)
        p.camera.up = up
        p.reset_camera()
        p.camera.zoom(1.15)
    p.screenshot(a.out)
    print(a.out)


if __name__ == "__main__":
    sys.exit(main())
