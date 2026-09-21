#!/usr/bin/env python3
"""Copy the six verified unique halves into all eight named PCB pairs."""
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from make_layout_pcbs import LAYOUTS, source_layout  # noqa: E402


# Every generated pair is a combination of one of two unique left halves and
# one of four unique right halves.  These representatives are independently
# finished and DRC-checked before this script is run.
REPRESENTATIVES = {
    ("Left", "wkl"): "wkl",
    ("Left", "wklarrows"): "three-key-left-wkl-right",
    ("Right", "wkl"): "three-key-left-wkl-right",
    ("Right", "wklarrows"): "wkl-left-arrows-right",
    ("Right", "wklbs2"): "wklbs2",
    ("Right", "wklbs2arrows"): "wkl-left-arrows-right-bs2",
}


def board_path(layout, side):
    return (ROOT / "pcb/variants/layouts" / layout /
            f"Symm60HE-{layout}-{side}.kicad_pcb")


def report_path(board):
    return board.with_name(board.stem + "-drc.rpt")


def main():
    for layout in LAYOUTS:
        for side in ("Left", "Right"):
            build = source_layout(layout, side)
            representative = REPRESENTATIVES[(side, build)]
            source = board_path(representative, side)
            target = board_path(layout, side)
            source_report = report_path(source)
            target_report = report_path(target)
            if not source_report.is_file():
                raise RuntimeError(f"missing verified report: {source_report}")
            if source != target:
                shutil.copy2(source, target)
                shutil.copy2(source_report, target_report)
            print(f"{layout:34} {side}: {build} from {representative}")


if __name__ == "__main__":
    main()
