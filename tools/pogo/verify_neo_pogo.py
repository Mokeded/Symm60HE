#!/usr/bin/env python3
"""Run DRC and structural checks for the Neo-style pogo variant."""
from pathlib import Path
import glob
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
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
            contact_pads = [pad for pad in find(footprints["PS1"], "pad")
                            if str(pad[1]).isdigit()]
            ffc_pads = [pad for pad in find(footprints["JF1"], "pad")
                        if str(pad[1]).isdigit()]
            assert len(contact_pads) == 12
            assert len(ffc_pads) == 12
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
            # The interior tongues follow the local diagonal edge, so their
            # axis-aligned bounding boxes can legitimately be wider than they
            # are tall.  Check the physical tongue envelope instead: all use
            # the same nominal 5.5 x 14 mm envelope (5 mm projection plus the
            # 0.5 mm buried root), with only the
            # lower interior tip allowed a small split-axis trim.
            rectangle = tab.minimum_rotated_rectangle
            corners = list(rectangle.exterior.coords)[:-1]
            edges = [((corners[(index + 1) % 4][0] - corners[index][0]) ** 2 +
                      (corners[(index + 1) % 4][1] - corners[index][1]) ** 2) ** 0.5
                     for index in range(4)]
            short, long = min(edges), max(edges)
            assert 5.45 <= short <= 5.55, (half, short, tab.bounds)
            assert 13.5 <= long <= 14.05, (half, long, tab.bounds)
            assert 65.5 <= tab.area <= 66.5, (half, tab.area, tab.bounds)
        print(f"{half} plate: four matching short smooth gasket mounts")
    print("Neo-style direct-target pogo verification: PASS")


if __name__ == "__main__":
    main()
