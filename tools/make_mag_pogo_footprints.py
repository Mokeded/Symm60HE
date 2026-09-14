#!/usr/bin/env python3
"""Write the magnetic pogo footprint pair from the ICD constants.

Kept separate from the board generator so a supplier drawing can be dropped in
by editing numbers here and re-running, rather than by redrawing a footprint.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_mag_pogo import BODY, PER_ROW, PITCH, ROW_GAP  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "Symm60HE_Project.pretty"
PAD = 1.50          # SUNMON 905-00030 recommends 2.00; see README
ANCHOR = 3.2
CRTYD = (BODY[0] + 1.0, BODY[1] + 1.0)
MAG_D = 4.0
MAG_X = BODY[0] / 2 - 2.0      # magnet centres, inboard of the housing ends
NAME = f"MagPogo_2x{PER_ROW}_P{int(PITCH * 100):03d}"


def lands(swap_rows):
    xs = [(i - (PER_ROW - 1) / 2) * PITCH for i in range(PER_ROW)]
    rows = (ROW_GAP / 2, -ROW_GAP / 2) if swap_rows else (-ROW_GAP / 2, ROW_GAP / 2)
    return [(row * PER_ROW + i + 1, x, y)
            for row, y in enumerate(rows) for i, x in enumerate(xs)]


def render(kind, swap_rows, descr):
    ref = "PS**" if kind == "Spring" else "PT**"
    value = f"MAGPOGO-2x{PER_ROW}-P{int(PITCH * 100):03d}-{kind[0]}"
    out = [f'(footprint "{NAME}_{kind}"',
           '  (version 20240108) (generator "pcbnew") (layer "F.Cu")',
           f'  (descr "{descr}")',
           f'  (tags "magnetic pogo {kind.lower()} 2x{PER_ROW} {PITCH}mm")',
           f'  (property "Reference" "{ref}" (at 0 {-BODY[1] / 2 - 1.5} 0)'
           ' (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))',
           f'  (property "Value" "{value}" (at 0 {BODY[1] / 2 + 1.5} 0)'
           ' (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))',
           '  (property "Datasheet" "" (at 0 0 0) (layer "F.Fab") (hide yes)'
           ' (effects (font (size 1.27 1.27) (thickness 0.15))))',
           f'  (property "Description" "{2 * PER_ROW}-contact magnetic pogo'
           f' {kind.lower()} half, 2 x {PER_ROW} on {PITCH} mm, SMT" (at 0 0 0)'
           ' (layer "F.Fab") (hide yes)'
           ' (effects (font (size 1.27 1.27) (thickness 0.15))))',
           '  (attr smd)',
           f'  (fp_rect (start {-BODY[0] / 2} {-BODY[1] / 2})'
           f' (end {BODY[0] / 2} {BODY[1] / 2})'
           ' (stroke (width 0.12) (type solid)) (fill none) (layer "F.Fab"))',
           f'  (fp_rect (start {-CRTYD[0] / 2} {-CRTYD[1] / 2})'
           f' (end {CRTYD[0] / 2} {CRTYD[1] / 2})'
           ' (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))']
    for sign in (-1, 1):
        out.append(f'  (fp_line (start {-BODY[0] / 2} {sign * BODY[1] / 2})'
                   f' (end {BODY[0] / 2} {sign * BODY[1] / 2})'
                   ' (stroke (width 0.15) (type solid)) (layer "F.SilkS"))')
        out.append(f'  (fp_circle (center {sign * MAG_X} 0)'
                   f' (end {sign * MAG_X + MAG_D / 2} 0)'
                   ' (stroke (width 0.12) (type solid)) (fill none) (layer "F.Fab"))')
    first = lands(swap_rows)[0]
    out.append(f'  (fp_circle (center {first[1]} {first[2] - 1.5})'
               f' (end {first[1] + 0.3} {first[2] - 1.5})'
               ' (stroke (width 0.15) (type solid)) (fill none) (layer "F.SilkS"))')
    for number, x, y in lands(swap_rows):
        out.append(f'  (pad "{number}" smd circle (at {x} {y}) (size {PAD} {PAD})'
                   ' (layers "F.Cu" "F.Paste" "F.Mask"))')
    for index, sign in enumerate((-1, 1), start=1):
        out.append(f'  (pad "MP{index}" smd roundrect (at {sign * MAG_X} 0)'
                   f' (size {ANCHOR} {ANCHOR}) (roundrect_rratio 0.15)'
                   ' (layers "F.Cu" "F.Paste" "F.Mask"))')
    out.append(")")
    (LIB / f"{NAME}_{kind}.kicad_mod").write_text("\n".join(out) + "\n")
    return LIB / f"{NAME}_{kind}.kicad_mod"


def main():
    # The target mates face to face, so its rows are swapped relative to the
    # spring: after the board flip, target pin N lands on spring pin N.
    paths = [render("Spring", False,
                    f"Magnetic pogo spring half, {2 * PER_ROW} contacts in 2 rows "
                    f"of {PER_ROW} on a {PITCH} mm grid, magnets in the housing at "
                    "both ends. Built to ICD MAGPOGO; confirm against the supplier "
                    "drawing before release."),
             render("Target", True,
                    f"Magnetic pogo target half mating with {NAME}_Spring. "
                    "Built to ICD MAGPOGO; confirm against the supplier drawing.")]
    for path in paths:
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
