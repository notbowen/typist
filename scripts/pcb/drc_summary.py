"""Summarise a kicad-cli DRC JSON report and gate on it.

  python3 scripts/pcb/drc_summary.py report.json [--allow-unrouted] [--allow TYPE ...]

Exit 1 if there are error-severity violations (excluding --allow'ed types),
or unconnected items (unless --allow-unrouted). Warnings are listed but
never fail the gate.
"""
import argparse, collections, json, sys

ap = argparse.ArgumentParser()
ap.add_argument("report")
ap.add_argument("--allow-unrouted", action="store_true")
ap.add_argument("--allow", action="append", default=[], help="violation type to ignore")
a = ap.parse_args()
d = json.load(open(a.report))

fail = False
viol = d.get("violations", [])
errs = [v for v in viol if v["severity"] == "error" and v["type"] not in a.allow]
warns = collections.Counter(v["type"] for v in viol if v["severity"] == "warning")
unc = d.get("unconnected_items", [])
print(f"{a.report}: {len(errs)} errors, {sum(warns.values())} warnings, {len(unc)} unconnected")
for t, n in warns.most_common():
    print(f"  warning {t} x{n}")
for v in errs:
    where = "; ".join(f"{i['description']} @({i['pos']['x']:.2f},{i['pos']['y']:.2f})" for i in v["items"])
    print(f"  ERROR {v['type']}: {v['description']} :: {where}")
if errs:
    fail = True
if unc:
    nets = collections.Counter()
    for u in unc:
        for i in u["items"]:
            desc = i["description"]
            nets[desc.split("[")[1].split("]")[0] if "[" in desc else desc] += 1
    print("  unconnected nets:", ", ".join(f"{n}" for n, _ in nets.most_common(12)))
    if not a.allow_unrouted:
        fail = True
sys.exit(1 if fail else 0)
