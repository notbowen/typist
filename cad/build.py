"""Build the case for one half, run the fit check and export STEP/STL.

  .venv/bin/python cad/build.py build/pcb/left.geom.json build/cad/left

Writes into the output directory:
  case.step / case.stl        printable case, print orientation (bottom on z=0)
  assembly/*.stl              PCB + component envelopes + keep-outs (board frame
                              shifted like the case) for renders
  fit.json                    fit-check results
Exit code 1 if anything intersects the case.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from build123d import Pos, export_step, export_stl  # noqa: E402

import components  # noqa: E402
from boardgeom import Board  # noqa: E402
from case import CaseParams, build_case  # noqa: E402

TOL = 1e-3  # mm^3


def main(geom_path: str, out_dir: str) -> int:
    t0 = time.time()
    out = Path(out_dir)
    (out / "assembly").mkdir(parents=True, exist_ok=True)
    board = Board(geom_path)
    env = components.build(board)
    params = CaseParams()
    case, info = build_case(board, env, params)
    shift = Pos(0, 0, -info["z_floor"])

    report = {"geom": geom_path, "params": params.__dict__, "checks": {}, "ok": True}
    for kind, items in (("solid", env.solids), ("keepout", env.keepouts)):
        for name, part in items.items():
            t1 = time.time()
            vol = (case & part).volume
            ok = vol <= TOL
            report["checks"][name] = {"kind": kind, "intersection_mm3": round(vol, 4), "ok": ok,
                                      "s": round(time.time() - t1, 1)}
            report["ok"] &= ok
            export_stl(shift * part, str(out / "assembly" / f"{kind}-{name}.stl"), tolerance=0.05)

    # the PCB must actually rest on something: its footprint overlaps the ledge
    support_area = board.outline.difference(info["cavity_2d"]).area
    report["checks"]["pcb_supported"] = {"kind": "support", "ledge_area_mm2": round(support_area, 1),
                                         "ok": support_area > 0.15 * board.outline.area * 0.1}
    report["ok"] &= report["checks"]["pcb_supported"]["ok"]

    t1 = time.time()
    printed = shift * case
    export_step(printed, str(out / "case.step"))
    export_stl(printed, str(out / "case.stl"), tolerance=0.02, angular_tolerance=0.2)
    report["export_s"] = round(time.time() - t1, 1)
    bb = printed.bounding_box()
    report["case"] = {"volume_mm3": round(printed.volume, 1),
                      "size_mm": [round(bb.size.X, 2), round(bb.size.Y, 2), round(bb.size.Z, 2)],
                      "pcb_bottom_z": round(-info["z_floor"], 3)}
    report["seconds"] = round(time.time() - t0, 1)
    (out / "fit.json").write_text(json.dumps(report, indent=1))

    for name, c in report["checks"].items():
        print(f"  {'OK ' if c['ok'] else 'FAIL'} {name}: {({k: v for k, v in c.items() if k not in ('ok', 'kind')})}")
    print(f"case {report['case']['size_mm']} mm, {report['case']['volume_mm3']} mm^3 -> {out}/case.stl "
          f"({report['seconds']}s)")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
