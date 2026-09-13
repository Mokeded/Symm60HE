# Symm60HE Fusion 360 case-design reference

Open `Symm60HE-case-reference-assembly.step`, or run the add-in under
`fusion-setup/`, to start the case around the real assembled geometry. The
master STEP is a reference mechanism rather than a finished case.

It contains separately named solids for the split plates, 1.2 mm Neo Hall
PCBs, switches, keycaps, flat controller daughterboard, both 20 x 6 mm
floating FFC-to-pogo PCBs, both Mill-Max 854 spring blocks, both directly
mounted 856 targets, spring-travel keepouts, controller ZIF envelopes and two
flexible FFC route envelopes. The controller is oriented left-to-right: its
USB-C receptacle and plug keepout pass directly through the rear case wall,
while J2 and J3 face the left and right interconnects.

The plate is the mechanical datum. Each plate, its Hall PCB, and its floating
pogo head move together on a mirrored 3 degree tent and 7 degree typing-angle
plane. The plate bottom is 6.5 mm above the Hall-PCB bottom. The target/spring
boards are 6.0 mm apart, which places the selected spring model within its
published stroke and makes its tips meet the target faces. The controller is
rigid and flat beneath the centre blocker; the cyan ribbon solids reserve
clearance and slack for independent gasket movement.

`Symm60HE-case-reference-assembly.FCStd` is the editable generated source.
The legacy `Symm60HE-reference-assembly.step` and `.FCStd` names are updated to
the same integrated geometry for compatibility. Individual globally positioned
STEP files are also supplied for the major boards, plates, switches and
keycaps.

Set `SYMM60HE_VISUAL_LAYOUT` to `doe-wkl`, `doe-wklbs2`, `doe-wklarrows`, or
`doe-wklbs2arrows` before regeneration to preview another supported layout.
The simplified switch/keycap solids are clearance references, not vendor CAD.

This reference does not establish a finished enclosure or physical fit. Pogo
compression, retention clearances, FFC bend life, Hall noise, gasket motion,
keycap-wall clearance and controller service access still require a prototype.

The original 20 x 20 mm floating-head interference has been removed. The two
20 x 6 mm heads keep the target rows in their electrically correct positions
and retain approximately 0.418 mm projected clearance at the centre seam.
Their F.Cu spring blocks and B.Cu FFC connectors are included as explicit case
reference solids.
