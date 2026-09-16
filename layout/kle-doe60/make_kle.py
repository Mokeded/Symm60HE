"""Write KLE files that put the four builds on the DOE 60%'s own curvature.

Rows 1-4 are the DOE's measured key centres and rotations, taken off the
published KLE render at 1u = 54 px by fitting a minimum-area rectangle to each
key face; the fitted angles land on whole multiples of 3 deg, so they are used
as measured.  The DOE's bottom row is WKL-blocked where these builds fit keys,
so row 5 is constructed instead: the build's own keys chained edge to edge
along the same 0/5/9 deg path the DOE's bottom row follows.

The right half is an exact mirror of the left about the measured axis, which
the DOE render is symmetric to within a fifth of a key.

Run from this directory:  python3 make_kle.py
"""
import json, math, os

U_PER_ROW = 1.0

# Left half, measured: (x, y, rotation_deg, width_u, label), u from the Esc centre.
R1 = [(0.000, 0.000, 0, 1.0, "Esc"), (0.992, 0.000, 0, 1.0, "1"),
      (1.993, 0.000, 0, 1.0, "2"),   (3.007, 0.041, 3, 1.0, "3"),
      (4.025, 0.148, 6, 1.0, "4"),   (5.034, 0.293, 9, 1.0, "5"),
      (6.041, 0.455, 9, 1.0, "6")]
R2 = [(0.072, 0.993, 0, 1.5, "Tab"), (1.315, 0.995, 0, 1.0, "Q"),
      (2.331, 1.014, 3, 1.0, "W"),   (3.331, 1.102, 6, 1.0, "E"),
      (4.327, 1.208, 6, 1.0, "R"),   (5.332, 1.352, 9, 1.0, "T"),
      (6.321, 1.508, 9, 1.0, "Y")]
R3 = [(0.158, 2.000, 0, 1.75, "Caps Lock"), (1.551, 2.000, 0, 1.0, "A"),
      (2.571, 2.022, 3, 1.0, "S"),   (3.598, 2.139, 6, 1.0, "D"),
      (4.607, 2.269, 9, 1.0, "F"),   (5.600, 2.431, 9, 1.0, "G")]
R4 = [(0.305, 2.990, 0, 2.25, "Shift"), (1.901, 2.990, 0, 1.0, "Z"),
      (2.925, 3.041, 3, 1.0, "X"),   (3.931, 3.175, 6, 1.0, "C"),
      (4.945, 3.336, 9, 1.0, "V"),   (5.937, 3.495, 9, 1.0, "B")]

ROW5_Y = 4.016      # measured bottom-row centreline where the row is unrotated
ROW5_LEFT = -0.820  # row 4's left extent: where the DOE's WKL blocker begins
MIRROR = 7.4305     # measured half-to-half mirror axis

# Right-half legends, inner to outer (left to right as rendered).
RIGHT = {
    "r1": ["7", "8", "9", "0", "-", "=", "]"],
    "r2": ["Y", "U", "I", "O", "P", "[", "Backspace"],
    "r3": ["H", "J", "K", "L", ";", "Enter"],
    "r4": ["B", "N", "M", ",", ".", "Shift"],
    "r5": ["Space", "Alt", "Super", "Control"],
    "r5arrows": ["Space", "Alt", "←", "↓", "→"],
}

def chain(items, x0=ROW5_LEFT, y0=ROW5_Y):
    """Lay out a bottom row edge to edge along the DOE's bottom-row path."""
    out, px, py = [], x0, y0
    for w, rot, label in items:
        a = math.radians(rot)
        cx, cy = px + (w / 2) * math.cos(a), py + (w / 2) * math.sin(a)
        out.append((round(cx, 3), round(cy, 3), rot, w, label))
        px, py = cx + (w / 2) * math.cos(a), cy + (w / 2) * math.sin(a)
    return out

R5 = chain([(1.5, 0, "Control"), (1.5, 0, "Fn"), (1.5, 5, "Alt"), (2.25, 9, "Space")])
R5_ARROWS = chain([(1.0, 0, "Control"), (1.0, 0, "Fn"), (1.0, 0, "Super"),
                   (1.5, 5, "Alt"), (2.25, 9, "Space")])

def mirror(row, legends):
    """Mirror a left-half row about the layout axis, inner to outer."""
    out = [(round(MIRROR * 2 - x, 3), y, -rot, w, lab)
           for (x, y, rot, w, lab) in row]
    out.reverse()
    assert len(legends) == len(out), "legend count must match key count"
    return [(x, y, rot, w, lab) for (x, y, rot, w, _), lab in zip(out, legends)]

def split_backspace(row):
    """The two outermost 1u keys of row 1 become one 2u Backspace."""
    a, b = row[-2], row[-1]
    return row[:-2] + [(round((a[0] + b[0]) / 2, 3), b[1], b[2], 2.0, "Backspace")]

def split_shift(row):
    """The 2.25u right Shift becomes 1u up-arrow plus 1.25u Shift."""
    x, y, rot, w, _ = row[-1]
    edge = x - w / 2
    return row[:-1] + [(round(edge + 0.5, 3), y, rot, 1.0, "↑"),
                       (round(edge + 1.625, 3), y, rot, 1.25, "Shift")]

def build(bs2, arrows):
    left = R1 + R2 + R3 + R4 + (R5_ARROWS if arrows else R5)
    r1 = mirror(R1, RIGHT["r1"])
    r2 = mirror(R2, RIGHT["r2"])
    r3 = mirror(R3, RIGHT["r3"])
    r4 = mirror(R4, RIGHT["r4"])
    r5 = mirror(R5_ARROWS if arrows else R5,
                RIGHT["r5arrows"] if arrows else RIGHT["r5"])
    if bs2:
        r1 = split_backspace(r1)
        r2 = [(x, y, rot, w, "]" if lab == "Backspace" else lab)
              for (x, y, rot, w, lab) in r2]
    if arrows:
        r4 = split_shift(r4)
    return left + r1 + r2 + r3 + r4 + r5

def relabel(row, legends):
    return [(x, y, rot, w, lab) for (x, y, rot, w, _), lab in zip(row, legends)]

# The reference file keeps the DOE's own legends as they read on the render.
REF_ROWS = [relabel(R1, ["Esc", "1", "2", "3", "4", "5", "6"]),
            relabel(R2, ["Esc", "Q", "W", "E", "R", "T", "7"]),
            relabel(R3, ["Tab", "A", "S", "D", "F", "G"]),
            relabel(R4, ["Shift", "Z", "X", "C", "V", "B"]),
            chain([(1.0, 0, "Opt"), (1.5, 5, "CMD"), (3.0, 9, "")], x0=1.032)]
REF_RIGHT = [["7", "8", "9", "0", "+", "~", ""],
             ["Y", "U", "I", "O", "P", "", "Bs"],
             ["H", "J", "K", "L", "", "enter"],
             ["B", "N", "M", "<", ">", "Shift"],
             ["Space", "CMD", ">"]]

def to_kle(keys):
    """One rotation cluster per key: rx/ry on the key centre, so r spins in place."""
    rows = []
    for x, y, rot, w, label in keys:
        prop = {"r": rot, "rx": round(x, 3), "ry": round(y, 3),
                "y": -0.5, "x": round(-w / 2, 4)}
        if w != 1.0:
            prop["w"] = w
        rows.append([prop, label])
    return rows

BUILDS = {"doe-wkl": (False, False), "doe-wklbs2": (True, False),
          "doe-wklarrows": (False, True), "doe-wklbs2arrows": (True, True)}

def write(name, keys):
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, name + ".kle.json"), "w") as f:
        json.dump(to_kle(keys), f, separators=(",", ":"))
    print("%-20s %d keys" % (name, len(keys)))

if __name__ == "__main__":
    for name, (bs2, arrows) in BUILDS.items():
        write(name, build(bs2, arrows))
    ref = [k for row in REF_ROWS for k in row]
    for row, legends in zip(REF_ROWS, REF_RIGHT):
        ref += mirror(row, legends)
    write("doe60-reference", ref)
