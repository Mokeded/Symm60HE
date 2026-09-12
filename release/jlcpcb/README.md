# Symm60HE JLCPCB release

The two keyboard halves are connected in `Symm60HE-Half-Panel-Gerbers.zip` as a 175.32 x 233.91 mm stacked panel with 5 mm routed rails, thirteen 5-hole mouse-bite rows at 0.75 mm pitch, three global B.Cu fiducials, four 2 mm tooling holes and all SMT components on B.Cu. Order that ZIP as one assembled PCB. Order the compact mixed-side daughterboard separately with `Symm60HE-Daughterboard-Gerbers.zip`; it has three local fiducials on each assembly side. Both designs are 2-layer, 1.2 mm finished thickness. The generated BOMs contain only fitted SMT parts and every line has an exact LCSC assignment. Choose exactly one matched BOM/CPL pair under the half-panel's `layouts/` directory; the universal panel must not be assembled from an all-positions placement list.

Gerbers include both copper layers, both solder masks, both silkscreens and Edge.Cuts. Silkscreen was clipped to solder-mask openings during plotting.

The panel's right board universal-layout arrow/2.25u-shift alternatives contain one pair of tangent NPTH holes. Confirm this merged/tangent drill geometry in JLC's Gerber viewer before payment; use a layout-specific PCB if JLC rejects it.
