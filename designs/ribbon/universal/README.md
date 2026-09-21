# Universal ribbon PCB

**Status: current prototype-order manufacturing candidate.**

One fully populated left/right PCB pair supports the four principal physical
layouts. Firmware masks the inactive Hall channels for the selected layout.

## Sources and manufacturing files

- [Left PCB source](../../../pcb/Symm60HE-Left.kicad_pcb)
- [Right PCB source](../../../pcb/Symm60HE-Right.kicad_pcb)
- [Connected manufacturing panel source](../../../pcb/Symm60HE-Panel.kicad_pcb)
- [Half-panel Gerber archive](../../../release/jlcpcb/Symm60HE-Half-Panel-Gerbers.zip)
- [Half-panel BOM and CPL](../../../release/jlcpcb/Symm60HE-Half-Panel/)
- [Daughterboard order](../../../release/jlcpcb/Symm60HE-Daughterboard/)
- [Order checklist](../../../release/jlcpcb/ORDER-CHECKLIST.md)

## Supported firmware profiles

| Profile | Bottom row | Right cluster | Backspace |
|---|---|---|---|
| `wkl` | WKL | standard | 2u |
| `wklarrows` | WKL | arrows | 2u |
| `wklbs2` | WKL | standard | split 1u + 1u |
| `wklbs2arrows` | WKL | arrows | split 1u + 1u |

## Matching mechanical files

- [Universal left plate](../../../plate/Symm60HE-plate-universal-left.dxf)
- [Universal right plate](../../../plate/Symm60HE-plate-universal-right.dxf)
- [Universal gasket pads](../../../plate/Symm60HE-gasket-pads-universal.dxf)
- [Complete populated Fusion reference](../../../case/fusion360/Symm60HE-reference-assembly.step)
- [Straight-on top view](../../../docs/img/17j-fusion-true-top-reference.png)

The universal right PCB uses four routed, unplated 1.75 mm alignment slots.
Confirm those slots in the fabricator's Gerber viewer before payment.
