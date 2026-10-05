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
specification. Gateron's `DS-02-001-A0` drawing controls the vertical switch
stack: each Hall PCB top is 5.00 mm below the switch flange/plate-top seating
plane. Consequently, the underside of each 1.50 mm plate is 3.50 mm above its
PCB top, and the switch lower housing reaches the PCB without an artificial
gap. The daughterboard is
centered at the rear on the split axis, remains flat across the lateral tent,
shares the same 7 degree typing angle, and sits 7 mm below the Hall-PCB datum.
The blue ribbon solids connect the actual current FPC coordinates and reserve
a 12 mm wide, 0.3 mm thick service-loop path below the gasket planes. The
0.3 mm thickness, 12 conductors at 1.0 mm pitch, same-side contacts and 100 mm
stock length correspond to JXTCONN `FC-1012P-100T3` / LCSC `C37635129`, but a
flex cable has no single production shape: the shown solid is the installed
bend/service envelope, not a claim that JXTCONN publishes a rigid STEP. They
rise outside the daughterboard perimeter and enter the outward-facing J2/J3
mouths across the F.Cu/top surface rather than passing through its underside. There is
deliberately no case solid: build new top and bottom components around these
reference bodies.

The switches and keycaps show the primary 60-key `doe-wkl` configuration, with
30 populated positions on each half. Each switch is a detailed five-part
Gateron KS-20 Magnetic Jade `KS-20TF10B045NW-Y89` reference: separate jade
lower housing, transparent sloped upper housing, white wall stem, swept spring,
and centre magnet. Gateron's official `DS-02-001-A0` drawing constrains the
15.40 x 15.10 mm upper envelope, 13.97 mm plate body, 15.00 x 14.70 mm
lower/clip envelope, 11.10 mm height, 5.00 mm lower body, 4.00 x 1.30 mm MX
cross, and both 1.70 mm locating pins on the PCB's matching +/-5.08 mm centres.
The remaining visible construction follows Gateron's official product and
exploded views. Gateron does not publish a production STEP, so this is a
verified product-form reference rather than proprietary mold geometry. A
separate inspectable STEP is under
`models/reference/gateron-ks20-magnetic-jade/`.

The caps use licensed full thin-wall Cherry-profile CAD measured from molded
caps, with the correct width and R1/R2/R3/R4 sculpt for each physical key. This is the closest
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

The three populated-component bodies are generated separately so LEDs, Hall
sensors, muxes, passives, MCU, crystal, power circuitry and other fitted
electronics can be shown or hidden without changing the PCB reference solids.
They no longer use generic KiCad package bodies. Every fitted electrical
footprint is rebuilt from either a manufacturer STEP or the STEP asset linked
to that exact fitted LCSC part in the **JLCEDA/EasyEDA Official Library**
([JLCEDA](https://lceda.cn/), [EasyEDA](https://easyeda.com/)). Shared C0402,
R0402, C0603 and SOT-23-3 geometry is reused only where each exact part record
links to the same official model UUID. `generated/component-model-coverage.json`
records every footprint, fitted/DNP status, part identity, model and source.

The routed halves use a TSSOP-16 footprint. Their verified model is therefore
TI `SN74LV4051APWR` / LCSC `C7793`, the active TSSOP-16 PW ordering code, rather
than the older `Symm60HE-BOM.csv` entry `SN74LV4051ADR` / `C128414`, which is a
physically incompatible SOIC-16 package. The 3D handoff does not hide that BOM
mismatch by placing a SOIC body on TSSOP pads.

The four 12-way FPC sockets use the exact LCSC-part-linked asset for BOOMELE
C20111. The HRO C165948 USB-C receptacle reuses the exact vendor solid and
native coordinate frame from the first validated assembly (`f18a949`) together
with its corrected placement convention (`4bc6caa`). Its mating mouth projects
0.6 mm through the rear daughterboard wall. Both buttons use XKB's
manufacturer-published `TS-1187A-B-A-B.stp`. Source URLs, official-library
UUIDs, baseline revisions and SHA-256 hashes are recorded under
`models/official/provenance.json`; required source attribution is retained in
`models/official/JLCEDA-EasyEDA-OFFICIAL-LIBRARY-NOTICE.md`.

One unresolved production identity remains explicit rather than being replaced
with a look-alike: the PCB calls out five `STAB_MX` / “Cherry PCB-mount
stabiliser” positions but the BOM supplies no manufacturer part number. Their
holes and plate clearances are exact; a certifiable stabilizer solid requires
the intended stabilizer SKU. Mounting holes are apertures, not fitted bodies.

The controller body now comes from
`pcb/Symm60HE-Daughterboard.kicad_pcb`. Its verified
case envelope is 49.5 x 29.2 mm at the configured 1.2 mm board thickness. The
USB-C, both FFC connectors, both buttons and all four M2 mounting-hole centres
retain their prior case datums, so the smaller outline can replace the former
50 x 31 mm daughterboard reference without moving the openings or standoffs.

### Compact daughterboard case datums

The following coordinates are in the daughterboard's flat local frame, with
`X=0, Y=0` at the minimum-X/minimum-Y Edge.Cuts corner. They are provided for
parametric case sketches; importing the STEP remains the authoritative method
for curved edges, holes and fitted-component clearances.

| Feature | Local X (mm) | Local Y (mm) |
| --- | ---: | ---: |
| MHD1, rear-left 2.2 mm NPTH | 2.7500 | 3.2633 |
| MHD3, rear-right 2.2 mm NPTH | 46.7500 | 3.2633 |
| MHD4, front-left 2.2 mm NPTH | 2.7500 | 27.7367 |
| MHD2, front-right 2.2 mm NPTH | 46.7500 | 27.7367 |
| J1 USB-C footprint centre | 24.7500 | 3.6500 |
| J2 left FFC footprint centre | 2.4500 | 15.5000 |
| J3 right FFC footprint centre | 47.0500 | 15.5000 |
| SW1 footprint centre | 12.5410 | 10.2633 |
| SW2 footprint centre | 19.0410 | 22.9633 |

The USB opening is on the minimum-Y/rear edge. The official HRO receptacle
solid projects 0.600 mm beyond that edge. The blue ribbon bodies are service
and bend-clearance envelopes rather than rigid case parts; keep them visible
while defining the internal cable corridors, then hide them for exterior work.

`Symm60HE-reference-assembly.FCStd` is the editable source assembly used to
create the STEP file. The individual STEP files are provided when importing
each reference as a separate Fusion component is preferable.

The PCB bodies are generated from the completed FN40HE-style universal left
and right boards and the compact FPC-matched daughterboard under `pcb/`.
`generated/reference-layout.json` records each exact source path, SHA-256
digest, Edge.Cuts bounds, and placement centre so the Fusion handoff can be
audited against those routed source files.
The build also reopens the generated STEP/FCStd artifacts and rejects a PCB
whose solid dimensions, source digest, stackup-compatible body thickness, or
named assembly body does not match that manifest. It additionally enforces a
minimum component-solid count and rejects a populated component body displaced
from its matching PCB.

Each plate half has two rear/top and two front/bottom integral gasket tongues;
the side edges carry no gasket mounts. The verifier rejects plate-to-plate,
plate-to-daughterboard, daughterboard-to-Hall-PCB, and ribbon-to-plate
intersections so the reference cannot silently regenerate overlapping geometry.

Historical case and pogo experiments are not part of this current-build tree.
Only the ribbon-connected production reference assembly and its rebuild inputs
are retained here.

## Componentized import

`Symm60HECaseSetup/` is a Fusion script that builds the same reference as a
componentized project rather than one imported body: each half's plate,
switches and keycaps as one component, each Hall PCB and the controller
daughterboard on their own, the ribbon routes grouped and hidden, and five
empty components to model the case into. It grounds the reference and checks
that nothing imported empty.

Copy that folder into Fusion's scripts directory — on Windows
`%APPDATA%\Autodesk\Autodesk Fusion 360\API\Scripts`, on macOS
`~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/Scripts` — and
run it from **Utilities > Scripts and Add-Ins**. Installed outside the
repository it cannot find these files on its own, so set
`SYMM60HE_REFERENCE_DIR` to this folder, or edit `REFERENCE_DIR` at the top of
the script.
