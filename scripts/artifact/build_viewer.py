"""Bundle the real design outputs into one self-contained interactive HTML viewer.

  .venv/bin/python scripts/artifact/build_viewer.py build/artifact/sweep-xiao.html

Reads (per side): build/pcb/<side>.geom.json, build/pcb/<side>-drc.json,
build/cad/<side>/{case.stl, fit.json, mesh.json, assembly/*.stl}; optional
build/pcb/<side>-routed... is not needed (placement is identical).
The STLs are embedded as base64, the PCB is rebuilt from its outline + pads so
it can carry a pad/hole texture. Everything else in the page is static text in
scripts/artifact/viewer_template.html.
"""
import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "cad"))
from components import DIMS  # noqa: E402
from case import CaseParams  # noqa: E402

PARTS = {  # assembly STL -> (group, colour)
    "solid-mcu_MCU1.stl": ("mcu", "#2b4c8c"),
    "solid-pwr_T1.stl": ("parts", "#1d1d1f"),
    "solid-jst_J1.stl": ("parts", "#f2efe6"),
    "solid-battery.stl": ("battery", "#b8bcc6"),
    "solid-under_pcb.stl": ("sockets", "#d9d4c7"),
    "keepout-usb_MCU1.stl": ("keepouts", "#ff4d4d"),
    "keepout-pwr_access_T1.stl": ("keepouts", "#ff4d4d"),
    "keepout-jst_plug_J1.stl": ("keepouts", "#ff4d4d"),
}


def b64(p: Path) -> str:
    return base64.b64encode(p.read_bytes()).decode()


def side_data(side: str) -> dict:
    g = json.loads((ROOT / f"build/pcb/{side}.geom.json").read_text())
    fit = json.loads((ROOT / f"build/cad/{side}/fit.json").read_text())
    mesh = json.loads((ROOT / f"build/cad/{side}/mesh.json").read_text())
    drc = json.loads((ROOT / f"build/pcb/{side}-drc.json").read_text())
    asm = ROOT / f"build/cad/{side}/assembly"
    keys = [[f["x"], f["y"], f["rot"]] for f in g["footprints"] if f["name"] == "PG1350"]
    pads = [{"l": p["layers"], "p": [[round(x, 3), round(y, 3)] for x, y in p["poly"]]} for p in g["pads"] if p["poly"]]
    holes = [[n["x"], n["y"], n["d"]] for n in g["npth"]] + \
            [[p["x"], p["y"], 0.8] for p in g["pads"] if p["type"] == "pth"]
    fps = [{k: f[k] for k in ("ref", "name", "x", "y", "rot", "side")} for f in g["footprints"]
           if f["name"] not in ("PG1350", "D_SOD-123")]
    drc_err = [v for v in drc.get("violations", []) if v.get("severity") == "error"]
    return {
        "outline": g["outline"][0], "thickness": g["thickness"], "keys": keys, "pads": pads,
        "holes": holes, "fps": fps, "tracks": g.get("tracks", []), "vias": g.get("vias", []),
        "pcb_bottom_z": fit["case"]["pcb_bottom_z"], "case_size": fit["case"]["size_mm"],
        "case_volume": fit["case"]["volume_mm3"],
        "checks": {k: v for k, v in fit["checks"].items()},
        "mesh": {"wall_p01": mesh["wall"]["p01"], "overhang": mesh["overhang"]["area_mm2"],
                 "watertight": mesh.get("watertight"), "fails": mesh.get("fails", [])},
        "drc": {"errors": len(drc_err), "unconnected": len(drc.get("unconnected_items", [])),
                "warnings": sum(1 for v in drc.get("violations", []) if v.get("severity") == "warning")},
        "case_stl": b64(ROOT / f"build/cad/{side}/case.stl"),
        "parts": [{"group": grp, "color": col, "stl": b64(asm / n)} for n, (grp, col) in PARTS.items() if (asm / n).exists()],
    }


def slice_info(side: str) -> dict:
    gcode = ROOT / f"build/cad/{side}/case.gcode"
    out = {}
    if gcode.exists():
        for line in gcode.read_text(errors="ignore").splitlines()[-400:]:
            if line.startswith("; total filament used [g]"):
                out["grams"] = line.split("=")[1].strip()
            if line.startswith("; estimated printing time (normal mode)"):
                out["time"] = line.split("=")[1].strip()
    return out


def main(out: str):
    data = {
        "sides": {s: side_data(s) for s in ("left", "right")},
        "slice": {s: slice_info(s) for s in ("left", "right")},
        "dims": {k: v for k, v in DIMS.items()},
        "case": CaseParams().__dict__,
    }
    tpl = (ROOT / "scripts/artifact/viewer_template.html").read_text()
    html = tpl.replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":")))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(html)
    print(f"{out}: {len(html) / 1e6:.2f} MB")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "build/artifact/sweep-xiao.html"))
