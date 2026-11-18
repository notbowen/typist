"""Printability checks for an STL (in print orientation).

  .venv/bin/python scripts/cad/verify_mesh.py part.stl [--min-wall 1.2]
        [--bed 220x220x250] [--overhang 45] [--json out.json]

Checks (FAIL = exit 1):
  watertight / consistent winding / positive volume / single body
  sits on the bed (min z == 0) and fits the build volume
  thin walls: ray-cast thickness sampled over the surface (5th percentile and
              fraction below --min-wall). Thin = FAIL if > 0.5 % of samples.
Reports (never fail): overhang area steeper than --overhang deg off vertical
that is not on the bed (needs supports or a chamfer).
"""
import argparse
import json
import sys

import numpy as np
import trimesh


def thickness_samples(m, n=4000, seed=0):
    rng = np.random.default_rng(seed)
    pts, fi = trimesh.sample.sample_surface(m, n, seed=int(rng.integers(1 << 31)))
    normals = m.face_normals[fi]
    origins = pts - normals * 1e-3
    locs, idx_ray, _ = m.ray.intersects_location(origins, -normals, multiple_hits=False)
    th = np.full(n, np.inf)
    th[idx_ray] = np.linalg.norm(locs - origins[idx_ray], axis=1)
    return th[np.isfinite(th)], pts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stl")
    ap.add_argument("--min-wall", type=float, default=1.2)
    ap.add_argument("--bed", default="220x220x250")
    ap.add_argument("--overhang", type=float, default=45)
    ap.add_argument("--json")
    a = ap.parse_args()

    m = trimesh.load(a.stl, force="mesh")
    res, fails = {"file": a.stl}, []
    bodies = m.split(only_watertight=False)
    res.update(
        faces=len(m.faces), watertight=bool(m.is_watertight), winding_consistent=bool(m.is_winding_consistent),
        volume_mm3=round(float(m.volume), 2), bodies=len(bodies),
        bbox_min=[round(float(v), 3) for v in m.bounds[0]], size_mm=[round(float(v), 2) for v in m.extents],
    )
    if not m.is_watertight:
        fails.append("mesh is not watertight")
    if not m.is_winding_consistent:
        fails.append("inconsistent winding")
    if m.volume <= 0:
        fails.append("non-positive volume (inverted normals?)")
    if len(bodies) != 1:
        fails.append(f"{len(bodies)} separate bodies")
    if abs(m.bounds[0][2]) > 1e-3:
        fails.append(f"min z is {m.bounds[0][2]:.3f}, not on the bed")
    bed = sorted(float(v) for v in a.bed.split("x")[:2]) + [float(a.bed.split("x")[2])]
    xy = sorted(m.extents[:2])
    if xy[0] > bed[0] or xy[1] > bed[1] or m.extents[2] > bed[2]:
        fails.append(f"size {m.extents.round(1).tolist()} exceeds bed {a.bed}")

    th, _ = thickness_samples(m)
    thin = float((th < a.min_wall - 1e-3).mean()) if len(th) else 0.0
    res["wall"] = {"min_wall": a.min_wall, "p01": round(float(np.percentile(th, 1)), 3),
                   "p05": round(float(np.percentile(th, 5)), 3), "median": round(float(np.median(th)), 3),
                   "thin_fraction": round(thin, 4)}
    if thin > 0.005:
        fails.append(f"{thin:.1%} of sampled surface is thinner than {a.min_wall} mm")

    # overhangs: downward-facing faces steeper than the limit, excluding the bed layer
    nz = m.face_normals[:, 2]
    limit = -np.cos(np.radians(a.overhang))
    centres_z = m.triangles_center[:, 2]
    over = (nz < limit) & (centres_z > 0.2)
    res["overhang"] = {"deg": a.overhang, "area_mm2": round(float(m.area_faces[over].sum()), 1),
                       "flat_bridges_mm2": round(float(m.area_faces[(nz < -0.99) & (centres_z > 0.2)].sum()), 1)}
    res["ok"] = not fails
    res["fails"] = fails

    print(json.dumps(res, indent=1))
    if a.json:
        open(a.json, "w").write(json.dumps(res, indent=1))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
