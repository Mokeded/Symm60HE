#!/usr/bin/env python3
"""Apply the three small, DRC-proven cleanups left after plane stitching.

These edits are intentionally explicit and deterministic.  They preserve the
autorouter's completed signal solution while freeing one trapped GND island on
each half and providing legal head-on GND escapes for MCU pins 31 and 63.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from route import seg, via  # noqa: E402
from sexp import dumps, find, first, loads  # noqa: E402


def segment_key(item):
    a, b = first(item, "start"), first(item, "end")
    return tuple(round(float(v), 4) for v in (a[1], a[2], b[1], b[2]))


def remove_segments(board, net, pairs):
    pairs = {tuple(round(v, 4) for v in p) for p in pairs}
    reverse = {(p[2], p[3], p[0], p[1]) for p in pairs}
    board[1:] = [item for item in board[1:]
                 if not (isinstance(item, list) and item and item[0] == "segment" and
                         first(item, "net")[1] == net and
                         segment_key(item) in pairs.union(reverse))]


def append(board, items):
    insert = next((i for i in range(len(board)-1, 0, -1)
                   if isinstance(board[i], list) and board[i] and
                   board[i][0] == "embedded_fonts"), len(board))
    board[insert:insert] = items


def reference(footprint):
    return next((p[2] for p in find(footprint, "property")
                 if p[1] == "Reference"), "")


def move_footprint(board, ref, x, y):
    fp = next(fp for fp in find(board, "footprint") if reference(fp) == ref)
    at = first(fp, "at")
    at[1], at[2] = x, y


def clean_left(board):
    move_footprint(board, "MHL3", 105.0, 30.0)
    old = {
        (27.2447, 56.4715, 27.2447, 54.5588),
        (46.3966, 57.5816, 28.3548, 57.5816),
        (27.2447, 54.5588, 25.3397, 52.6538),
        (25.3397, 52.6538, 25.3397, 50.5247),
        (28.3548, 57.5816, 27.2447, 56.4715),
    }
    remove_segments(board, "MUX_A2", old)
    path = [(25.3397, 50.5247), (25.3397, 49.8), (24.4, 48.8603),
            (23.8, 49.4603), (23.8, 58.4), (45.5782, 58.4),
            (46.3966, 57.5816)]
    items = [seg(path[i], path[i+1], "MUX_A2", "B.Cu")
             for i in range(len(path)-1)]
    items += [seg((27.8797, 55.4747), (26.6097, 55.4747), "GND", "B.Cu"),
              via((42.4822, 54.525), "GND")]
    append(board, items)


def clean_right(board):
    move_footprint(board, "MHR1", 195.0, 30.0)
    remove_segments(board, "+3V3A", {
        (207.5740, 61.0619, 207.5510, 60.3022),
        (207.2090, 61.0160, 207.5740, 61.0619),
    })
    fp = next(fp for fp in find(board, "footprint") if reference(fp) == "CR27A")
    at = first(fp, "at")
    at[1], at[2] = 216.0, 56.0
    p1, p2 = (215.52023, 56.01484), (216.47977, 55.98516)
    v1, v2 = (214.72023, 56.03984), (217.27977, 55.96016)
    append(board, [seg(p1, v1, "+3V3A", "B.Cu"), via(v1, "+3V3A"),
                   seg(p2, v2, "GND", "B.Cu"), via(v2, "GND")])


def clean_daughterboard(board):
    remove_segments(board, "+3V3A", {
        (181.3331, 16.0498, 180.6568, 16.7261),
        (180.6568, 16.7261, 153.4165, 16.7261),
        (153.4165, 16.7261, 152.1941, 17.9485),
        (152.1941, 17.9485, 139.8333, 17.9485),
    })
    path = [(181.3331, 16.0498), (180.6568, 16.7261), (158.0, 16.7261),
            (156.0, 18.7261), (153.2, 18.7261), (151.2, 20.7261),
            (142.6109, 20.7261), (139.8333, 17.9485)]
    items = [seg(path[i], path[i+1], "+3V3A", "F.Cu")
             for i in range(len(path)-1)]
    items += [seg((152.459, 15.9117), (152.459, 17.0), "GND", "F.Cu"),
              via((152.459, 17.0), "GND"),
              seg((145.959, 4.5617), (145.959, 3.3), "GND", "F.Cu"),
              via((145.959, 3.3), "GND")]
    append(board, items)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1] / "pcb"
    for name, operation in (("Symm60HE-Left", clean_left),
                            ("Symm60HE-Right", clean_right),
                            ("Symm60HE-Daughterboard", clean_daughterboard)):
        path = root / (name + ".kicad_pcb")
        board = loads(path.read_text())
        operation(board)
        path.write_text(dumps(board) + "\n")
        print("cleaned", path.name)
