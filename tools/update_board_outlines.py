#!/usr/bin/env python3
"""Replace only the three PCB Edge.Cuts with the current solid outlines.

The routed board text is otherwise preserved byte-for-byte.  This deliberately
does not call mkboards.py, because regenerating a board would discard the
hand-finished routing and zones.
"""
import re
import uuid
from pathlib import Path

from outline import LEFT_PCB, RIGHT_PCB, DB

ROOT = Path(__file__).resolve().parent.parent
BLOCK = re.compile(r"\n\t\(gr_(?:line|arc|rect|poly)\n.*?\n\t\)", re.DOTALL)


def edge_block(a, b):
    return (
        "\n\t(gr_line\n"
        f"\t\t(start {a[0]:.4f} {a[1]:.4f})\n"
        f"\t\t(end {b[0]:.4f} {b[1]:.4f})\n"
        "\t\t(stroke\n\t\t\t(width 0.1)\n\t\t\t(type solid)\n\t\t)\n"
        "\t\t(layer \"Edge.Cuts\")\n"
        f"\t\t(uuid \"{uuid.uuid4()}\")\n\t)"
    )


def replace(name, polygon):
    path = ROOT / "pcb" / f"{name}.kicad_pcb"
    text = path.read_text()
    removed = 0

    def keep_or_remove(match):
        nonlocal removed
        block = match.group(0)
        if '(layer "Edge.Cuts")' in block:
            removed += 1
            return ""
        return block

    updated = BLOCK.sub(keep_or_remove, text)
    points = list(polygon.exterior.coords)
    edges = "".join(edge_block(a, b) for a, b in zip(points, points[1:]))
    marker = updated.find("\n\t(segment")
    if marker < 0:
        raise RuntimeError(f"{name}: no insertion point")
    updated = updated[:marker] + edges + updated[marker:]
    if removed == 0 or updated.count('(layer "Edge.Cuts")') != len(points) - 1:
        raise RuntimeError(f"{name}: unsafe Edge.Cuts replacement")
    path.write_text(updated)
    print(f"{name}: replaced {removed} old edges with {len(points) - 1} solid-outline edges")


replace("Symm60HE-Left", LEFT_PCB)
replace("Symm60HE-Right", RIGHT_PCB)
replace("Symm60HE-Daughterboard", DB)
