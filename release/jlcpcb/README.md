# Symm60HE JLCPCB release

The two keyboard halves are connected in `Symm60HE-Half-Panel-Gerbers.zip` as a 162.29 x 227.83 mm stacked panel with routed rails, thirteen 5-hole mouse-bite rows at 0.75 mm pitch, three global B.Cu fiducials, four 2 mm tooling holes and all SMT components on B.Cu. Order that ZIP as one assembled PCB. Order the 50 x 31 mm compact mixed-side daughterboard separately with `Symm60HE-Daughterboard-Gerbers.zip`; it retains only its four symmetric M2 NPTH case mounts and has no local fiducial footprints. Both designs are 2-layer, 1.2 mm finished thickness. The generated BOMs contain every fitted universal-layout Hall sensor, all ten muxes and the reverse-mount RGB LEDs. Every line has an exact LCSC assignment. Use the single matched BOM/CPL pair: every assembled board supports all four physical layouts, while firmware profiles mask the inactive Hall channels.

Gerbers include both copper layers, both solder masks, both silkscreens and Edge.Cuts. Silkscreen was clipped to solder-mask openings during plotting.

The panel's right board uses four explicit 1.75 mm-wide routed NPTH slots where mutually exclusive universal-layout alignment holes overlap. Confirm all four unplated slots in the fabricator viewer before payment.
