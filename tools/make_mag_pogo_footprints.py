#!/usr/bin/env python3
"""Write the SUNMON MC142-09R footprint pair from the published drawings.

903-00081 (MC142-09R-BM) and 904-00080 (MC142-09R-JF) are a DIP PCB-mount
magnetic pair: nine contacts in two staggered rows, an N and an S magnet at the
ends keying the mate, and a 4.50 mm tall body. Every dimension below is read
off those two drawings; nothing here is invented.

The magnets sit inside the housing, above the board, so the land pattern is
nine plated holes and nothing else.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "Symm60HE_Project.pretty"

PITCH = 1.50          # along a row, both rows
ROW_GAP = 1.25        # between the two rows
LOWER = 5             # contacts 1-5, the longer row
UPPER = 4             # contacts 6-9, offset half a pitch
CONTACT_DIA = 1.20    # contact face, drawing
TAIL_DIA = 0.50       # tail, drawing
DRILL = 0.80          # tail + 0.30 clearance
PAD = 1.25            # leaves 0.21 mm to the nearest diagonal neighbour
BODY = {"Spring": (19.80, 8.30), "Target": (21.80, 8.30)}
PART = {"Spring": ("903-00081", "MC142-09R-BM"),
        "Target": ("904-00080", "MC142-09R-JF")}
NAME = "MagPogo_9_MC142"


def lands(mirror):
    """Contact centres. Pins 1-5 on the lower row, 6-9 offset half a pitch."""
    out = []
    for index in range(LOWER):
        out.append((index + 1, (index - (LOWER - 1) / 2) * PITCH, -ROW_GAP / 2))
    for index in range(UPPER):
        out.append((LOWER + index + 1, (index - (UPPER - 1) / 2) * PITCH, ROW_GAP / 2))
    return [(n, x, -y if mirror else y) for n, x, y in out]


def render(kind, mirror):
    width, height = BODY[kind]
    part, legacy = PART[kind]
    crtyd = (width + 1.0, height + 1.0)
    out = [f'(footprint "{NAME}_{kind}"',
           '  (version 20240108) (generator "pcbnew") (layer "F.Cu")',
           f'  (descr "SUNMON {part} ({legacy}), 9-contact magnetic pogo '
           f'{kind.lower()} half. Two staggered rows on {PITCH} mm pitch, '
           f'{ROW_GAP} mm between rows, {CONTACT_DIA} mm contacts, '
           f'{TAIL_DIA} mm DIP tails. Magnets are internal: N52 NdFeB at both '
           'ends of the housing, keyed N to S, so the land pattern is the nine '
           'holes only.")',
           f'  (tags "SUNMON {part} magnetic pogo 9 contact DIP")',
           f'  (property "Reference" "{"PS**" if kind == "Spring" else "PT**"}"'
           f' (at 0 {-height / 2 - 1.4} 0) (layer "F.SilkS")'
           ' (effects (font (size 0.8 0.8) (thickness 0.12))))',
           f'  (property "Value" "{part}" (at 0 {height / 2 + 1.4} 0)'
           ' (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))',
           '  (property "Datasheet" "https://smeconn.com/product/'
           '9-pin-double-row-magnetic-connector/" (at 0 0 0) (layer "F.Fab")'
           ' (hide yes) (effects (font (size 1.27 1.27) (thickness 0.15))))',
           f'  (property "Description" "9-contact magnetic pogo {kind.lower()}'
           f' half, SUNMON {part}, DC 12 V 1 A, 50 mOhm max, 0.70 mm full'
           ' stroke" (at 0 0 0) (layer "F.Fab") (hide yes)'
           ' (effects (font (size 1.27 1.27) (thickness 0.15))))',
           '  (attr through_hole)',
           f'  (fp_rect (start {-width / 2} {-height / 2})'
           f' (end {width / 2} {height / 2})'
           ' (stroke (width 0.12) (type solid)) (fill none) (layer "F.Fab"))',
           f'  (fp_rect (start {-crtyd[0] / 2} {-crtyd[1] / 2})'
           f' (end {crtyd[0] / 2} {crtyd[1] / 2})'
           ' (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))']
    for sign in (-1, 1):
        out.append(f'  (fp_line (start {-width / 2} {sign * height / 2})'
                   f' (end {width / 2} {sign * height / 2})'
                   ' (stroke (width 0.15) (type solid)) (layer "F.SilkS"))')
    first = lands(mirror)[0]
    out.append(f'  (fp_circle (center {first[1]} {first[2] - 1.35})'
               f' (end {first[1] + 0.3} {first[2] - 1.35})'
               ' (stroke (width 0.15) (type solid)) (fill none) (layer "F.SilkS"))')
    for number, x, y in lands(mirror):
        shape = "rect" if number == 1 else "circle"
        out.append(f'  (pad "{number}" thru_hole {shape} (at {x} {y})'
                   f' (size {PAD} {PAD}) (drill {DRILL})'
                   ' (layers "*.Cu" "*.Mask"))')
    out.append(")")
    path = LIB / f"{NAME}_{kind}.kicad_mod"
    path.write_text("\n".join(out) + "\n")
    return path


def main():
    # The target mates face to face, so its rows are swapped relative to the
    # spring: after the board flip, target pin N lands on spring pin N.
    for path in (render("Spring", False), render("Target", True)):
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
