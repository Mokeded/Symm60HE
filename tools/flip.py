"""Flip a footprint to the back copper.

Rule taken from FN40HE's own flipped footprints: y negated, x unchanged,
F.* layers become B.*, and a placed pad's angle is its library angle plus the
footprint rotation.
"""
from sexp import Sym, find, first

SWAP = {"F.Cu":"B.Cu","B.Cu":"F.Cu","F.Mask":"B.Mask","B.Mask":"F.Mask",
        "F.Paste":"B.Paste","B.Paste":"F.Paste","F.SilkS":"B.SilkS","B.SilkS":"F.SilkS",
        "F.Fab":"B.Fab","B.Fab":"F.Fab","F.CrtYd":"B.CrtYd","B.CrtYd":"F.CrtYd"}
YPAIR = {"at", "start", "end", "center", "mid", "xy"}

def flip(node):
    """In place: mirror about the x axis and move F layers to B."""
    if not isinstance(node, list): return
    if node and node[0] in YPAIR and len(node) >= 3:
        try: node[2] = -float(node[2])
        except (TypeError, ValueError): pass
    if node and node[0] == "layer" and len(node) == 2 and node[1] in SWAP:
        node[1] = SWAP[node[1]]
    if node and node[0] == "layers":
        node[1:] = [SWAP.get(l, l) for l in node[1:]]
    for c in node:
        if isinstance(c, list): flip(c)

def set_pad_angles(fp, fprot):
    """Placed pad angle = library angle + footprint rotation."""
    for p in find(fp, "pad"):
        a = first(p, "at")
        if a is None: continue
        lib = float(a[3]) if len(a) > 3 else 0.0
        ang = round((lib + fprot) % 360, 3)
        if len(a) > 3: a[3] = ang
        else: a.append(ang)
