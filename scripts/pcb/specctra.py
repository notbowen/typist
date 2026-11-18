"""pcbnew helper (runs inside the KiCad container via scripts/kicad).

  python3 specctra.py export board.kicad_pcb out.dsn [edge_clearance_mm]
  python3 specctra.py import board.kicad_pcb in.ses out.kicad_pcb

Freerouting ignores KiCad's copper-to-edge clearance, so the export adds a
temporary track/via keep-out ring along Edge.Cuts (default 0.9 mm wide) to the
DSN only; the board file itself is never modified.
"""
import sys
import pcbnew


def add_edge_keepout(board, width_mm):
    outline = pcbnew.SHAPE_POLY_SET()
    if not board.GetBoardPolygonOutlines(outline):
        sys.exit("board outline (Edge.Cuts) is not closed")
    grown, inner = outline.CloneDropTriangulation(), outline.CloneDropTriangulation()
    grown.Inflate(pcbnew.FromMM(1.0), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, pcbnew.FromMM(0.01))
    inner.Inflate(pcbnew.FromMM(-width_mm), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, pcbnew.FromMM(0.01))
    grown.BooleanSubtract(inner)
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetDoNotAllowTracks(True)
    z.SetDoNotAllowVias(True)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowCopperPour(False)
    z.SetDoNotAllowFootprints(False)
    ls = pcbnew.LSET()
    ls.AddLayer(pcbnew.F_Cu)
    ls.AddLayer(pcbnew.B_Cu)
    z.SetLayerSet(ls)
    z.Outline().RemoveAllContours()
    z.Outline().Append(grown)
    board.Add(z)


cmd = sys.argv[1]
board = pcbnew.LoadBoard(sys.argv[2])
if cmd == "export":
    add_edge_keepout(board, float(sys.argv[4]) if len(sys.argv) > 4 else 0.9)
    ok = pcbnew.ExportSpecctraDSN(board, sys.argv[3])
elif cmd == "import":
    ok = pcbnew.ImportSpecctraSES(board, sys.argv[3])
    if ok:
        # Refill any copper zones so DRC sees the final copper.
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        board.Save(sys.argv[4])
else:
    sys.exit(f"unknown command {cmd}")
if not ok:
    sys.exit(f"specctra {cmd} failed")
