# Symm60HE Fusion 360 case-design references

`Symm60HE-reference-assembly.step` is the primary Fusion 360 handoff. Import
it with **File > Open > Upload** and save the imported design as a Fusion
project. It contains fourteen separately named reference bodies:

- Left PCB
- Right PCB
- Daughterboard PCB
- Left PCB components
- Right PCB components
- Daughterboard components
- Left 12-way ribbon-cable clearance envelope
- Right 12-way ribbon-cable clearance envelope
- Left universal plate
- Right universal plate
- Left switches
- Right switches
- Left keycaps
- Right keycaps

The two keyboard halves are each shown at 3 degrees from horizontal—left at
-3 degrees and right at +3 degrees, for a 6 degree included angle—and a rear-up 7 degree
typing angle. The plate bodies are 1.5 mm thick, matching the locked POM plate
specification. Each Hall PCB is 5 mm below its plate. The daughterboard is
centered at the rear on the split axis, remains flat across the lateral tent,
shares the same 7 degree typing angle, and sits 7 mm below the Hall-PCB datum.
The blue ribbon solids connect the actual current FPC coordinates and reserve
a 12 mm wide, 0.3 mm thick service-loop path below the gasket planes. They
rise outside the daughterboard perimeter and enter the outward-facing J2/J3
mouths across the F.Cu/top surface rather than passing through its underside. There is
deliberately no case solid: build new top and bottom components around these
reference bodies.

The switches and keycaps show the primary 60-key `doe-wkl` configuration, with
30 populated positions on each half. The switches are dimensional Gateron
KS-20 Magnetic Jade `KS-20TF10B045NW-Y89` references reconstructed from
Gateron's official `DS-02-001-A0` drawing: the model includes the 15.40 x 15.10
mm upper envelope, 13.97 mm plate body, 15.00 x 14.70 mm lower/clip envelope,
11.10 mm height, 5.00 mm lower body, 4.00 x 1.30 mm MX cross and both 1.70 mm
locating pins on the PCB's matching +/-5.08 mm centres. Gateron does not
publish a production STEP, so this is an exterior dimensional reconstruction,
not proprietary mold geometry.

The caps use licensed thin-wall Cherry-profile reference CAD with the correct
width and R1/R2/R3/R4 sculpt for each physical key. This is the closest
auditable public CAD equivalent of GMK CYL: GMK publicly identifies CYL as the
original Cherry profile, 1.5 mm double-shot ABS with an MX-cross mount, but does
not publish its proprietary production surfaces. The assembly uses R1 on the
number row, R2 on QWERTY, R3 on the home row and R4 on both lower rows. The
exporter performs pairwise solid collision checks and records the minimum
clearance in `generated/switch-keycap-model-provenance.json`. Hide the switch
and cap bodies for PCB or plate work and show them to judge case-wall, blocker
and typing clearances.
Set `SYMM60HE_VISUAL_LAYOUT` to `doe-wkl`, `doe-wklbs2`, `doe-wklarrows`, or
`doe-wklbs2arrows` before running `build.sh` to regenerate another populated
layout.

The three populated-component bodies are generated separately from the current
KiCad footprint models so LEDs, Hall sensors, muxes, passives, MCU, crystal,
power circuitry and other fitted electronics can be shown or hidden without
changing the PCB reference solids. The four 12-way FPC sockets use the exact
LCSC-owned EasyEDA STEP asset for BOOMELE C20111. The HRO C165948 USB-C
receptacle reuses the exact vendor solid and native coordinate frame from the
first validated assembly (`f18a949`) together with its corrected placement
convention (`4bc6caa`). Its historical 180-degree body rotation is adapted to
the current board-coordinate pipeline, and its mating mouth projects 0.6 mm
through the rear daughterboard wall. This avoids the opposite coordinate frame
of the newer EasyEDA conversion. Both buttons use XKB's manufacturer-published
`TS-1187A-B-A-B.stp`. The source URLs, identifiers, baseline revisions and
SHA-256 hashes are recorded under `models/official/provenance.json`. Only rigid
placement transforms are applied, and the USB-C projection beyond the
daughterboard edge is preserved.

`Symm60HE-reference-assembly.FCStd` is the editable source assembly used to
create the STEP file. The individual STEP files are provided when importing
each reference as a separate Fusion component is preferable.

The PCB bodies are generated from the current packaged two-layer boards under
`work/enclosure-style-hotswap-freerouting-candidate/routed-final/`, not from
the older development copies under `pcb/`. `generated/reference-layout.json`
records each source path, SHA-256 digest, exact Edge.Cuts bounds, and placement
centre so the Fusion handoff can be audited against the routed release files.
The build also reopens the generated STEP/FCStd artifacts and rejects a PCB
whose solid dimensions, source digest, stackup-compatible body thickness, or
named assembly body does not match that manifest. It additionally enforces a
minimum component-solid count and rejects a populated component body displaced
from its matching PCB.

The opposing centre-side gasket tongues terminate with a controlled 2 mm gap.
The verifier rejects plate-to-plate, daughterboard-to-Hall-PCB, and
ribbon-to-plate intersections so the reference cannot silently regenerate the
previous overlapping geometry.

The previous case was removed from this directory. A hash-verified recovery
copy is retained under `work/recovery-case-20260911-0837/`.

`tenting-solution/` contains a separate editable 27-body fixed 6 degree
pogo/controller mechanism. It is intentionally independent from the empty
case-design reference assembly so it can be inserted, repositioned, or omitted
as one subsystem while the enclosure is modeled around the real PCBs and
plates.
