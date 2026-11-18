"""Add a copper pour for a net on both copper layers, filling the board outline.
Runs inside the KiCad container:
  scripts/kicad python3 scripts/pcb/add_zones.py in.kicad_pcb out.kicad_pcb [NET] [clearance_mm]
Existing zones on the same net are replaced.

Also adds a no-pour rule area on both layers under the XIAO's antenna end (the end
opposite USB-C) and a few mm beyond it: a ground plane right under the chip antenna
detunes it. Tracks and pads are still allowed there (the NFC/D6/D7 pads live there).
"""
import math
import sys
import pcbnew

src, dst = sys.argv[1], sys.argv[2]
net_name = sys.argv[3] if len(sys.argv) > 3 else "GND"
clearance = float(sys.argv[4]) if len(sys.argv) > 4 else 0.3

board = pcbnew.LoadBoard(src)
net = board.FindNet(net_name)
if net is None:
    sys.exit(f"net {net_name} not found")
for z in list(board.Zones()):
    if z.GetNetname() == net_name:
        board.Remove(z)

# antenna keep-out, in XIAO-local mm (x across the module, y from USB toward the antenna):
# the last 5 mm of the 21 mm module plus 3 mm beyond its end, 1.6 mm wider on each side
ANT = (-10.5, 5.5, 10.5, 13.5)
KEEPOUT_NAME = "antenna_no_pour"
for z in list(board.Zones()):
    if z.GetIsRuleArea() and z.GetZoneName() == KEEPOUT_NAME:
        board.Remove(z)
for fp in board.GetFootprints():
    if "XIAO" not in fp.GetFPID().GetLibItemName().wx_str():
        continue
    a = math.radians(fp.GetOrientationDegrees())
    o = fp.GetPosition()
    poly = pcbnew.SHAPE_POLY_SET()
    poly.NewOutline()
    for lx, ly in ((ANT[0], ANT[1]), (ANT[2], ANT[1]), (ANT[2], ANT[3]), (ANT[0], ANT[3])):
        # KiCad: y down, positive orientation is counter-clockwise on screen
        x = lx * math.cos(a) + ly * math.sin(a)
        y = -lx * math.sin(a) + ly * math.cos(a)
        poly.Append(o.x + pcbnew.FromMM(x), o.y + pcbnew.FromMM(y))
    k = pcbnew.ZONE(board)
    k.SetIsRuleArea(True)
    k.SetZoneName(KEEPOUT_NAME)
    k.SetDoNotAllowCopperPour(True)
    k.SetDoNotAllowTracks(False)
    k.SetDoNotAllowVias(False)
    k.SetDoNotAllowPads(False)
    k.SetDoNotAllowFootprints(False)
    ls = pcbnew.LSET()
    ls.AddLayer(pcbnew.F_Cu)
    ls.AddLayer(pcbnew.B_Cu)
    k.SetLayerSet(ls)
    k.Outline().RemoveAllContours()
    k.Outline().Append(poly)
    board.Add(k)
    print(f"added {KEEPOUT_NAME} rule area at {fp.GetReference()}")

# Freerouting sometimes necks a track down to 0.10-0.12 mm; keep to 0.15 mm (the DRC
# run after this catches any clearance that the wider track would break)
MIN_TRACK = pcbnew.FromMM(0.15)
thin = [t for t in board.GetTracks() if t.GetClass() != "PCB_VIA" and t.GetWidth() < MIN_TRACK]
for t in thin:
    t.SetWidth(MIN_TRACK)
if thin:
    print(f"widened {len(thin)} track segments to 0.15 mm")

outline = pcbnew.SHAPE_POLY_SET()
if not board.GetBoardPolygonOutlines(outline):
    sys.exit("board outline (Edge.Cuts) is not closed")

for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(net)
    z.SetLocalClearance(pcbnew.FromMM(clearance))
    z.SetMinThickness(pcbnew.FromMM(0.25))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)   # no floating copper
    # solid connection: the few GND pads here sit near the board edge, where
    # thermal reliefs end up with a single (starved) spoke
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    z.SetIsFilled(False)
    z.Outline().RemoveAllContours()
    z.Outline().Append(outline)
    board.Add(z)

pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.Save(dst)
print(f"added {net_name} pour on F.Cu/B.Cu -> {dst}")
