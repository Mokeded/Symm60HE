#!/usr/bin/env python3
"""Run DRC and structural checks for the Neo-style pogo variant."""
from pathlib import Path
import glob
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "pcb/variants/pogo-neo"
MODULES = tuple(f"Symm60HE-Neo-{side}-SpringModule"
                for side in ("Left", "Right"))
HALVES = tuple(f"Symm60HE-Neo-{side}-Half" for side in ("Left", "Right"))
BOARDS = ("Symm60HE-Neo-Controller",) + MODULES + HALVES

sys.path.insert(0, str(ROOT / "tools"))
from outline import (LEFT_GASKET_TABS, RIGHT_GASKET_TABS,  # noqa: E402
                     LEFT_PLATE_BODY, RIGHT_PLATE_BODY)
from sexp import find, first, loads  # noqa: E402


def find_cli():
    found = shutil.which("kicad-cli")
    if found:
        return found
    candidates = sorted(glob.glob(
        "/opt/homebrew/Caskroom/kicad/*/KiCad/KiCad.app/Contents/MacOS/kicad-cli"),
        reverse=True)
    if not candidates:
        raise RuntimeError("kicad-cli not found")
    return candidates[0]


def reference(fp):
    return next((prop[2] for prop in find(fp, "property")
                 if len(prop) > 2 and prop[1] == "Reference"), "")


def main():
    cli = find_cli()
    for name in BOARDS:
        board_path = OUT / f"{name}.kicad_pcb"
        report = OUT / f"{name}-drc.rpt"
        result = subprocess.run(
            [cli, "pcb", "drc", "--refill-zones", "--save-board",
             "--severity-all", "--exit-code-violations", "-o", str(report),
             str(board_path)], capture_output=True, text=True)
        text = report.read_text()
        assert result.returncode == 0, (name, result.stdout, result.stderr)
        assert "** Found 0 DRC violations **" in text, name
        assert "** Found 0 unconnected pads **" in text, name
        board = loads(board_path.read_text())
        copper = [layer[1] for layer in first(board, "layers")[1:]
                  if isinstance(layer, list) and str(layer[1]).endswith(".Cu")]
        assert copper == ["F.Cu", "B.Cu"], (name, copper)
        if name in MODULES:
            footprints = {reference(fp): fp for fp in find(board, "footprint")}
            assert set(footprints) == {"JF1", "PS1"}, footprints.keys()
            assert first(footprints["JF1"], "layer")[1] == "B.Cu"
            assert first(footprints["PS1"], "layer")[1] == "F.Cu"
            contact_pads = [pad for pad in find(footprints["PS1"], "pad")
                            if str(pad[1]).isdigit()]
            ffc_pads = [pad for pad in find(footprints["JF1"], "pad")
                        if str(pad[1]).isdigit()]
            assert len(contact_pads) == 12
            assert len(ffc_pads) == 12
            edge_points = []
            for line in find(board, "gr_line"):
                if first(line, "layer")[1] != "Edge.Cuts":
                    continue
                edge_points.extend((first(line, "start")[1:3],
                                    first(line, "end")[1:3]))
            xs = [float(point[0]) for point in edge_points]
            ys = [float(point[1]) for point in edge_points]
            assert (min(xs), max(xs), min(ys), max(ys)) == (0.0, 20.0, 0.0, 6.0)
            print(f"{name}: 20 x 6 mm, F.Cu spring / B.Cu FFC")
        elif name in HALVES:
            footprints = {reference(fp): fp for fp in find(board, "footprint")}
            side = "Left" if "Left" in name else "Right"
            old_ref = "JL1" if side == "Left" else "JR1"
            target_ref = "PTL1" if side == "Left" else "PTR1"
            assert old_ref not in footprints
            assert target_ref in footprints
            target_pads = [pad for pad in find(footprints[target_ref], "pad")
                           if str(pad[1]).isdigit()]
            assert len(target_pads) == 12
            print(f"{side.lower()} half: target mounted directly on Hall PCB")
        print(f"{name}: 0 violations, 0 unconnected, two copper layers")

    for half, body, tabs in (("left", LEFT_PLATE_BODY, LEFT_GASKET_TABS),
                             ("right", RIGHT_PLATE_BODY, RIGHT_GASKET_TABS)):
        assert len(tabs) == 4
        _, body_y0, _, body_y1 = body.bounds
        for tab in tabs:
            _, y0, _, y1 = tab.bounds
            assert y0 >= body_y0 - 1e-6 and y1 <= body_y1 + 1e-6
            assert tab.bounds[3] - tab.bounds[1] > tab.bounds[2] - tab.bounds[0]
        print(f"{half} plate: four side-only gasket tabs")
    print("Neo-style direct-target pogo verification: PASS")


if __name__ == "__main__":
    main()
