"""Add a copper pour for a net on both copper layers, filling the board outline.
Runs inside the KiCad container:
  scripts/kicad python3 scripts/pcb/add_zones.py in.kicad_pcb out.kicad_pcb [NET] [clearance_mm]
Existing zones on the same net are replaced.
"""
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

outline = pcbnew.SHAPE_POLY_SET()
if not board.GetBoardPolygonOutlines(outline):
    sys.exit("board outline (Edge.Cuts) is not closed")

for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(net)
    z.SetLocalClearance(pcbnew.FromMM(clearance))
    z.SetMinThickness(pcbnew.FromMM(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetIsFilled(False)
    z.Outline().RemoveAllContours()
    z.Outline().Append(outline)
    board.Add(z)

pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.Save(dst)
print(f"added {net_name} pour on F.Cu/B.Cu -> {dst}")
