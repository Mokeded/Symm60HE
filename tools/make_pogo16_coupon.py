#!/usr/bin/env python3
"""Generate routed 16-contact Mill-Max spring/target qualification coupons."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "pcb/variants/pogo/coupon"

PIN_NETS = {
    1: "GND", 2: "+3V3A", 3: "GND", 4: "+3V3A",
    5: "GND", 6: "MUX_A0", 7: "GND", 8: "MUX_A1",
    9: "GND", 10: "MUX_A2", 11: "GND", 12: "ADC_1",
    13: "ADC_2", 14: "ADC_3", 15: "GND", 16: "ADC_4",
}


def q(value):
    return '"' + value.replace('"', '\\"') + '"'


def connector(kind):
    spring = kind == "spring"
    name = ("MillMax_855-22-016-30-004101" if spring
            else "MillMax_857-10-016-30-051000")
    value = ("855-22-016-30-004101" if spring
             else "857-10-016-30-051000")
    reference = "PS1" if spring else "PT1"
    lines = [
        f'  (footprint "Symm60HE_Project:{name}"',
        '    (layer "F.Cu") (at 9 14)',
        f'    (property "Reference" {q(reference)} (at 0 -3 0) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))',
        f'    (property "Value" {q(value)} (at 0 3 0) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))',
        '    (attr smd)',
        '    (fp_rect (start -5.27 -1.27) (end 5.27 1.27) (stroke (width 0.12) (type solid)) (fill none) (layer "F.Fab"))',
        '    (fp_line (start -5.27 -1.27) (end 5.27 -1.27) (stroke (width 0.15) (type solid)) (layer "F.SilkS"))',
        '    (fp_circle (center -4.445 -1.85) (end -4.15 -1.85) (stroke (width 0.15) (type solid)) (fill none) (layer "F.SilkS"))',
    ]
    for pin in range(1, 17):
        column = (pin - 1) // 2
        x = -4.445 + column * 1.27
        y = -0.635 if pin % 2 else 0.635
        lines.append(
            f'    (pad {q(str(pin))} smd circle (at {x:.3f} {y:.3f}) '
            f'(size 0.96 0.96) (layers "F.Cu" "F.Paste" "F.Mask") '
            f'(net {pin} {q("P" + str(pin).zfill(2))}))')
    lines.append('  )')
    return "\n".join(lines)


def testpoint(pin):
    column = (pin - 1) // 2
    x = 4.555 + column * 1.27
    y = 4 if pin % 2 else 24
    return f'''  (footprint "TestPoint:THTPad_1.5x1.5mm_Drill0.8mm"
    (layer "F.Cu") (at {x:.3f} {y})
    (property "Reference" "TP{pin}" (at 0 -1.4 0) (layer "F.SilkS") (effects (font (size 0.55 0.55) (thickness 0.09))))
    (property "Value" "{PIN_NETS[pin]}" (at 0 1.4 0) (layer "F.Fab") (effects (font (size 0.55 0.55) (thickness 0.09))))
    (attr through_hole)
    (pad "1" thru_hole circle (at 0 0) (size 0.9 0.9) (drill 0.5) (layers "*.Cu" "*.Mask") (net {pin} "P{pin:02d}"))
  )'''


def mounting_hole(ref, x, y, diameter):
    return f'''  (footprint "MountingHole:{ref}"
    (layer "F.Cu") (at {x} {y})
    (property "Reference" "{ref}" (at 0 -2 0) (layer "F.SilkS") (effects (font (size 0.55 0.55) (thickness 0.09))))
    (property "Value" "ALIGNMENT" (at 0 2 0) (layer "F.Fab") (effects (font (size 0.55 0.55) (thickness 0.09))))
    (attr through_hole exclude_from_pos_files exclude_from_bom)
    (pad "" np_thru_hole circle (at 0 0) (size {diameter} {diameter}) (drill {diameter}) (layers "*.Cu" "*.Mask"))
  )'''


def board(kind):
    lines = ['''(kicad_pcb (version 20240108) (generator "pcbnew")
  (general (thickness 1.6))
  (paper "A4")
  (layers (0 "F.Cu" signal) (31 "B.Cu" signal) (36 "B.SilkS" user "b.silkscreen")
    (37 "F.SilkS" user "f.silkscreen") (44 "Edge.Cuts" user))
  (setup (pad_to_mask_clearance 0))''']
    lines.extend(f'  (net {pin} "P{pin:02d}")' for pin in range(1, 17))
    lines.append(connector(kind))
    lines.extend(testpoint(pin) for pin in range(1, 17))
    lines.append(mounting_hole("GUIDE1", 2.5, 14, 2.25))
    lines.append(mounting_hole("GUIDE2", 15.5, 14, 2.25))
    lines.append(mounting_hole("KEY", 15.5, 20.5, 2.85))
    for pin in range(1, 17):
        column = (pin - 1) // 2
        x = 4.555 + column * 1.27
        start_y = 13.365 if pin % 2 else 14.635
        end_y = 4 if pin % 2 else 24
        lines.append(f'  (segment (start {x:.3f} {start_y:.3f}) (end {x:.3f} {end_y}) (width 0.25) (layer "F.Cu") (net {pin}))')
    lines.extend([
        '  (gr_rect (start 0 0) (end 18 28) (stroke (width 0.1) (type solid)) (fill none) (layer "Edge.Cuts"))',
        f'  (gr_text "POGO16 {kind.upper()} - POWER OFF" (at 9 27) (layer "F.SilkS") (effects (font (size 0.75 0.75) (thickness 0.12))))',
        ')',
    ])
    return "\n".join(lines) + "\n"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for kind in ("spring", "target"):
        path = OUT / f"Symm60HE-Pogo16-{kind.title()}-Coupon.kicad_pcb"
        path.write_text(board(kind))
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
