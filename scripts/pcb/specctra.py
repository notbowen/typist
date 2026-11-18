"""pcbnew helper (runs inside the KiCad container via scripts/kicad).

  python3 specctra.py export board.kicad_pcb out.dsn
  python3 specctra.py import board.kicad_pcb in.ses out.kicad_pcb
"""
import sys
import pcbnew

cmd = sys.argv[1]
board = pcbnew.LoadBoard(sys.argv[2])
if cmd == "export":
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
