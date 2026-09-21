#!/usr/bin/env python3
"""Verify the isolated FR-4 serpentine pogo daughterboard prototype."""
from pathlib import Path
import math
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_serpentine_pogo import global_pad, prop  # noqa: E402
from sexp import find, first, loads  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
BOARD = ROOT / "pcb/variants/pogo-serpentine/Symm60HE-Serpentine-Daughterboard.kicad_pcb"
REPORT = ROOT / "pcb/variants/pogo-serpentine/Symm60HE-Serpentine-Daughterboard-drc.rpt"
MOVING_SPANS = ((118.7, 148.8), (217.6, 247.6))


def xy(item, key):
    node = first(item, key)
    return float(node[1]), float(node[2])


def in_moving_span(point):
    return any(lo < point[0] < hi for lo, hi in MOVING_SPANS)


def crossings(segments, probe_x):
    hits = []
    for item in segments:
        start, end = xy(item, "start"), xy(item, "end")
        if min(start[0], end[0]) <= probe_x < max(start[0], end[0]):
            hits.append(item)
    return hits


def main():
    board = loads(BOARD.read_text())
    report = REPORT.read_text()
    assert "** Found 0 DRC violations **" in report
    assert "** Found 0 unconnected pads **" in report

    thickness = float(first(first(board, "general"), "thickness")[1])
    assert math.isclose(thickness, 0.8), thickness

    footprints = {prop(fp, "Reference"): fp for fp in find(board, "footprint")}
    for reference in ("PSL1", "PSR1"):
        pads = [pad for pad in find(footprints[reference], "pad")
                if str(pad[1]).isdigit()]
        assert len(pads) == 16, (reference, len(pads))
        assert not any(in_moving_span(global_pad(footprints[reference], pad))
                       for pad in pads)

    vias = find(board, "via")
    assert not [item for item in vias if in_moving_span(xy(item, "at"))]

    segments = find(board, "segment")
    for probe_x in (130.0, 236.0):
        hits = crossings(segments, probe_x)
        assert len(hits) == 16, (probe_x, len(hits))
        assert {first(item, "layer")[1] for item in hits} == {"B.Cu"}
        assert all(math.isclose(float(first(item, "width")[1]), 0.18)
                   for item in hits)

    # Copper pours remain on the rigid controller island only.
    for zone in find(board, "zone"):
        for point in find(zone, "xy"):
            assert not in_moving_span((float(point[1]), float(point[2])))

    print("serpentine pogo verification: PASS")
    print("  0 DRC violations; 0 unconnected pads")
    print("  0.8 mm, 2-layer static-flex board")
    print("  16 B.Cu conductors per arm; no moving-span vias or pours")


if __name__ == "__main__":
    main()
