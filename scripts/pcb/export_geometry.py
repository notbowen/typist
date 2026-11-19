"""Export board geometry for the 3D viewer (scripts/artifact). Runs inside the KiCad container:

  scripts/kicad python3 scripts/pcb/export_geometry.py board.kicad_pcb out.json

Coordinates are millimetres in a CAD frame: x right, y UP (KiCad's y is flipped),
origin at the KiCad origin. Rotations are degrees, counter-clockwise.
JSON fields:
  thickness           board thickness
  outline             list of polygons (outer first, then holes), each [[x,y],...]
  footprints          [{ref, name, x, y, rot, side, bbox:[xmin,ymin,xmax,ymax]}]
  pads                [{ref, pad, net, x, y, layers, type, poly:[[x,y],...]}]
  npth                [{ref, x, y, d}]   non-plated holes (switch centre posts etc.)
  tracks              [[x1, y1, x2, y2, width, layer]]  copper tracks (for previews)
  vias                [[x, y, size, drill]]
  zones               [{layer, net, polys:[[outer, hole, ...], ...]}]  filled copper pours (visible
                      through a clear solder mask)
"""
import json, sys
import pcbnew

src, dst = sys.argv[1], sys.argv[2]
b = pcbnew.LoadBoard(src)
mm = pcbnew.ToMM

def pt(p):
    return [round(mm(p.x), 4), round(-mm(p.y), 4)]

def chain(c):
    return [pt(c.CPoint(i)) for i in range(c.PointCount())]

ps = pcbnew.SHAPE_POLY_SET()
if not b.GetBoardPolygonOutlines(ps):
    sys.exit("Edge.Cuts outline is not closed")
outline = []
for i in range(ps.OutlineCount()):
    outline.append(chain(ps.Outline(i)))
    for h in range(ps.HoleCount(i)):
        outline.append(chain(ps.Hole(i, h)))

fps, pads, npth = [], [], []
for f in b.GetFootprints():
    bb = f.GetBoundingBox(False)
    fps.append({
        "ref": f.GetReference(),
        "name": str(f.GetFPID().GetLibItemName()),
        "x": round(mm(f.GetPosition().x), 4), "y": round(-mm(f.GetPosition().y), 4),
        "rot": round(f.GetOrientationDegrees(), 3),
        "side": "bottom" if f.IsFlipped() else "top",
        "bbox": [mm(bb.GetLeft()), -mm(bb.GetBottom()), mm(bb.GetRight()), -mm(bb.GetTop())],
    })
    for p in f.Pads():
        if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
            npth.append({"ref": f.GetReference(), "x": pt(p.GetPosition())[0],
                         "y": pt(p.GetPosition())[1], "d": round(mm(p.GetDrillSizeX()), 3)})
            continue
        poly = pcbnew.SHAPE_POLY_SET()
        layer = pcbnew.B_Cu if p.IsOnLayer(pcbnew.B_Cu) and not p.IsOnLayer(pcbnew.F_Cu) else pcbnew.F_Cu
        p.TransformShapeToPolygon(poly, layer, 0, pcbnew.FromMM(0.01), pcbnew.ERROR_INSIDE)
        layers = [n for n, l in (("F.Cu", pcbnew.F_Cu), ("B.Cu", pcbnew.B_Cu)) if p.IsOnLayer(l)]
        pads.append({
            "ref": f.GetReference(), "pad": p.GetNumber(), "net": p.GetNetname(),
            "x": pt(p.GetPosition())[0], "y": pt(p.GetPosition())[1],
            "layers": layers,
            "type": {pcbnew.PAD_ATTRIB_PTH: "pth", pcbnew.PAD_ATTRIB_SMD: "smd"}.get(p.GetAttribute(), "other"),
            "poly": chain(poly.Outline(0)) if poly.OutlineCount() else [],
        })

tracks, vias = [], []
for t in b.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T:
        vias.append(pt(t.GetPosition()) + [round(mm(t.GetWidth(pcbnew.F_Cu)), 3), round(mm(t.GetDrillValue()), 3)])
    elif t.Type() == pcbnew.PCB_TRACE_T:
        tracks.append(pt(t.GetStart()) + pt(t.GetEnd()) + [round(mm(t.GetWidth()), 3), b.GetLayerName(t.GetLayer())])

zones = []
for z in b.Zones():
    if z.GetIsRuleArea():
        continue
    for lid in z.GetLayerSet().CuStack():
        if lid not in (pcbnew.F_Cu, pcbnew.B_Cu) or not z.HasFilledPolysForLayer(lid):
            continue
        fp = z.GetFilledPolysList(lid)
        polys = []
        for i in range(fp.OutlineCount()):
            polys.append([chain(fp.Outline(i))] + [chain(fp.Hole(i, h)) for h in range(fp.HoleCount(i))])
        if polys:
            zones.append({"layer": b.GetLayerName(lid), "net": z.GetNetname(), "polys": polys})

json.dump({
    "source": src,
    "thickness": round(mm(b.GetDesignSettings().GetBoardThickness()), 3),
    "outline": outline, "footprints": fps, "pads": pads, "npth": npth,
    "tracks": tracks, "vias": vias, "zones": zones,
}, open(dst, "w"), indent=1)
print(f"{dst}: {len(outline)} outline loops, {len(fps)} footprints, {len(pads)} pads, {len(npth)} npth, {len(zones)} zone fills")
