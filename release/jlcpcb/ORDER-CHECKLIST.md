# Symm60HE prototype-order checklist

Use these settings for both PCB orders unless the fabricator flags a specific incompatibility:

- 2 copper layers
- 1.2 mm finished FR-4 thickness
- 1 oz finished copper
- black solder mask and white silkscreen
- electrical test enabled
- via covering: tented (solder mask over vias). A few GND pads on the half boards carry a 0.6/0.3 mm via inside the pad where the south-side LED pocket left no other stitch path; tenting keeps those pads solderable and is the ordinary JLCPCB default
- order the half panel and daughterboard as separate assembly jobs

The separate switch plates are specified as 1.5 mm POM. Supply the selected `plate/Symm60HE-plate-*-left.dxf` and matching `-right.dxf` without rescaling; the plate fabricator must apply its own kerf compensation. Each plate half must retain two short outer-edge gasket tongues and two matching short centre-side tongues. Cut the correspondingly named `plate/Symm60HE-gasket-pads-<layout>.dxf` from 1.5 mm Poron; the unsuffixed gasket-pad file is the universal-layout alias. All eight mounts use the same smooth-tapered 5 mm projection. The finished plate web is at least 2.0 mm; Hype does not publish a numeric web limit, so request their final DXF review before ordering.

## Half-panel job

Upload `Symm60HE-Half-Panel-Gerbers.zip` with `Symm60HE-Half-Panel/Symm60HE-Half-Panel-BOM.csv` and `Symm60HE-Half-Panel/Symm60HE-Half-Panel-CPL.csv`. All fitted SMT parts are on B.Cu. In the Gerber viewer confirm the 162.34 x 227.88 mm plotted bounds, routed panel outline, thirteen mouse-bite rows, four tooling holes, three fiducials, every LED aperture, and all four right-board routed NPTH alignment slots used by mutually exclusive layout positions. Do not pay if a slot is deleted, rendered as overlapping drill hits or plated.

## Daughterboard job

Upload `Symm60HE-Daughterboard-Gerbers.zip` with `Symm60HE-Daughterboard/Symm60HE-Daughterboard-BOM.csv` and `Symm60HE-Daughterboard/Symm60HE-Daughterboard-CPL.csv`. This is a mixed-side assembly. Confirm that the assembler quotes both sides and that the Gerber viewer reports approximately 50.1 x 31.1 mm plotted bounds, four perimeter M2 NPTH mounts, two outward-facing FPC sockets and the rear-facing USB-C opening.

## Release identity

Run `shasum -a 256 -c release/jlcpcb/SHA256SUMS.txt` from the project root immediately before upload. The manifest covers the two Gerber archives, both BOM/CPL pairs, this documentation, the exact source PCBs, the firmware binary and its clean-build report.

Order prototype quantity first. Production quantity remains gated on physical plate/case/FFC fit and assembled Hall-noise testing.
