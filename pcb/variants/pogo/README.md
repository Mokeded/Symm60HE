# Symm60HE 16-contact magnetic pogo alternate

This is a separate prototype stream. It does **not** replace the checked
outward-facing FFC keyboard release under `release/jlcpcb`.

The selected interface is an orderable Mill-Max pair:

- `855-22-016-30-004101`: 16-contact, 2 × 8, 1.27 mm-pitch SMT spring block
- `857-10-016-30-051000`: matching 16-contact SMT gold target block

The KiCad library contains both footprints. `Symm60HE-pogo16-pinout.csv` fixes
the per-half electrical order, including redundant +3V3A and seven ground
contacts. The interface is deliberately power-off-only.

`coupon/` contains the routed spring and target qualification boards. Their
Gerbers, BOMs, checksums and zero-error/zero-unconnected DRC reports are in
`release/pogo16-prototype/`. These small boards are the correct first article:
they let the actual parts, solder lands, mechanical tolerance and mid-stroke
stack be measured before the expensive full keyboard boards are changed.

The tented mechanical architecture, pinout, validation gates and production
boundary are documented in `CONNECTOR-AND-TENTING.md`. Editable separate-body
CAD is in `case/fusion360/pogo-variant/`.

The obsolete custom 12-contact/ENIG feasibility boards were removed from the
active tree and retained under `.recovery/pogo12-superseded-*`.

The routed Neo-style rebuild is now under `../pogo-neo/`. It replaces each
half's FFC with a direct 12-contact target and uses only two floating spring
heads, each joined to the controller by one short 12-way FPC. This is
electrically complete and DRC-clean, but it remains a prototype until the coupon,
connector-stack, and Hall-noise gates pass.
