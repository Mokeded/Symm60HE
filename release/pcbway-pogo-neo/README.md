# Symm60HE PCBWay Neo-pogo manufacturing package

This release is independent of `release/jlcpcb-pogo-neo`. It contains production plots, drills, assembly PDFs, PCBWay BOMs and centroids for the five active 1.2 mm, two-layer boards and two customer-designed family panels.

## Recommended order

Order `family-panels/Hall-Family/fabrication/Hall-Family-Panel-Gerbers-and-Drills.zip` as a two-design panel with bottom-side assembly. Choose exactly one matching BOM/centroid pair under `assembly/layouts/`. Order `family-panels/Centre-Family/fabrication/Centre-Family-Panel-Gerbers-and-Drills.zip` as a three-design panel with both-side assembly. Do not combine a BOM from one layout with a centroid from another.

The `individual-boards/` tree is supplied for review, rework, and alternate quoting. Do not order an individual-board Gerber ZIP and its containing family panel for the same required quantity.

The Mill-Max 854 spring and 856 target placements are included by exact MPN. No substitute is authorized. PCBWay must confirm turnkey sourcing or customer consignment and manual-placement capability before production. See `PCBWay-RFQ-Notes.txt` and `Critical-Connector-Placements.csv`.

The assembly PDFs show physical reference geometry for both sides. The matched layout BOM and centroid are authoritative for which universal-layout Hall positions are fitted. Confirm every side and rotation in PCBWay's engineering review before payment.
