# Symm60HE Fusion 360 case-design reference

Run the add-in under `fusion-setup/` to start the case around the complete
assembled geometry. The setup imports globally positioned individual STEP
files into a native Fusion component hierarchy, including a standalone exact
HRO USB-C component whose checked J1 placement is baked into its B-rep. The
master STEP remains a convenient single-file reference mechanism rather than
the componentized import source.

The generated Fusion browser tree has these independent top-level reference
components:

- left plate + switches + keycaps
- right plate + switches + keycaps
- left Hall-effect PCB, including its directly mounted pogo target
- right Hall-effect PCB, including its directly mounted pogo target
- the fitted Hall sensor, capacitor and mux package bodies on both halves
- central controller daughterboard, including its fitted package bodies, both
  exact C20111 ZIF bodies, both exact C318884 buttons and the actual placed
  HRO USB-C receptacle
- left floating pogo daughterboard, spring block and ZIF body
- right floating pogo daughterboard, spring block and ZIF body
- one cable-and-movement-keepout component, hidden by default

Every individual STEP has its checked assembly transform baked into the B-rep
geometry. Do not regenerate these files by exporting the FCStd objects without
the project exporter: ordinary FreeCAD STEP occurrence transforms are not
preserved when Fusion imports a STEP into an existing child component, which
would return the small boards and pogo blocks to their local origins.

`Case - model here` remains a separate empty component and is activated at the
end of setup. Fusion therefore ghosts the grounded reference tree while case
geometry is being authored; activate the root to inspect everything opaque.

The Fusion setup contains separately named solids for the split plates, 1.2 mm
Neo Hall PCBs, their fitted KiCad package models, switches, keycaps, flat
controller daughterboard and its fitted package models, the actual
HRO TYPE-C-31-M-12 USB-C receptacle, both 20 x 6 mm
floating FFC-to-pogo PCBs, both Mill-Max 854 spring blocks, both directly
mounted 856 targets, spring-travel keepouts, four exact C20111 ZIF bodies and two
flexible FFC route envelopes. The controller is oriented left-to-right: its
USB-C receptacle and plug keepout pass directly through the rear case wall,
while J2 and J3 face the left and right interconnects.

The plate is the mechanical datum. Each plate, its Hall PCB, and its floating
pogo head move together on a mirrored 3 degree tent and 7 degree typing-angle
plane. To accommodate equal-size opposing centre gasket mounts, the complete
left and right moving assemblies are translated 2.75 mm outward per side
(5.50 mm additional split width); the controller remains centred and fixed.
The plate bottom is 6.5 mm above the Hall-PCB bottom. The target/spring
boards are 6.0 mm apart, which places the selected spring model within its
published stroke and makes its tips meet the target faces. The controller is
rigid and flat beneath the centre blocker; the cyan ribbon solids reserve
clearance and slack for independent gasket movement.

All eight integral plate gasket tongues now use a Neo-Ergo-inspired long
side-bearing geometry adapted to the plate: 24.0 mm overall edgewise length,
a 20.0 x 4.0 mm gasket-bearing area, 4.0 mm exposed projection and 0.6 mm root
inset. Broad 2.0 mm end transitions eliminate abrupt shoulders. The opposed
centre tongues retain a 0.50 mm flat-layout gap and clearance in the assembled
tented model.

The controller PCB has a 14 mm-wide, 1 mm-deep rear-edge setback beneath J1.
The actual HRO TYPE-C-31-M-12 shell remains on J1's footprint datum and
therefore overhangs the local PCB edge by exactly 1.0 mm. This setback is in
the KiCad Edge.Cuts geometry and is present in the manufacturing board, not
only in the Fusion visualization.

`Symm60HE-case-reference-assembly.FCStd` is the editable generated source and
contains the placed HRO receptacle. The combined assembly STEP intentionally
omits only that connector, but the componentized Fusion setup imports
`Symm60HE-ControllerUSBConnector.step`. The exporter applies the verified
rotation and translation to the underlying exact vendor TopoShape before it
writes that standalone STEP, leaving Fusion no nested vendor transform to
reinterpret. The verifier now imports that file again and checks its complete
bounding box against the exact placed HRO source. The add-in also checks every
imported component against `generated/component-placement.json` before setup
completes.
The legacy `Symm60HE-reference-assembly.step` and `.FCStd` names are updated to
the same integrated geometry for compatibility. Individual globally positioned
STEP files are also supplied for the major boards, plates, switches and
keycaps.

Set `SYMM60HE_VISUAL_LAYOUT` to `doe-wkl`, `doe-wklbs2`, `doe-wklarrows`, or
`doe-wklbs2arrows` before regeneration to preview another supported layout.
The switch bank now represents the selected XVX Whisper EC/HE switch and its
published MX-stem, N-pole-down and 3.5 +/- 0.2 mm-travel configuration. XVX
does not publish an exact mechanical STEP or dimensioned housing drawing, so it
remains a product-specific clearance reference rather than manufacturer CAD.
The keycap bank uses row-specific Cherry R1-R4 depth and tilt from the open
KeyV2 Cherry profile. An exact keycap-kit CAD model can only replace it after a
specific keycap manufacturer and kit are selected.

The USB-C, both tactile buttons and all four FFC connector bodies are now exact,
source-locked LCSC/EasyEDA models for C165948, C318884 and C20111. Their URLs,
model UUIDs and SHA-256
digests are recorded in `models/model-provenance.json`; run
`python tools/verify_model_provenance.py` to detect replacement or corruption.
These are exact distributor EDA models, which is stronger than a generic
package but is not mislabeled as manufacturer-certified CAD.

Exact Mill-Max 854/856 CAD is published through Mill-Max's verified supplier
catalog, but downloading it requires a 3D ContentCentral account. Until those
two files are supplied, the assembly deliberately retains the dimensioned
published-envelope models and identifies them as fallbacks. See
`models/vendor/README.md` for the exact filenames and configuration rules.

This reference does not establish a finished enclosure or physical fit. Pogo
compression, retention clearances, FFC bend life, Hall noise, gasket motion,
keycap-wall clearance and controller service access still require a prototype.

The original 20 x 20 mm floating-head interference has been removed. The two
20 x 6 mm heads keep the target rows in their electrically correct positions
and retain approximately 0.418 mm projected clearance at the centre seam.
Their F.Cu spring blocks and B.Cu FFC connectors are included as explicit case
reference solids.
