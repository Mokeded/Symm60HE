# Unrouted PCB starters

This folder contains the two WKL fixed-layout routing starters in `wkl-fixed-layout/` and 49 additional boards in `remaining/`.

All copies have their copper track segments and vias removed while retaining board geometry, nets, and component footprints. Muxes use the compact `AM1_TSSOP-16_4.4x5mm_P0.65mm` footprint. Shared mux, Hall sensor, and Hall capacitor placements follow the uploaded WKL routing checkpoints; variant-specific panel offsets are preserved where a board uses a translated layout. The `remaining/manifest.csv` records the source board and per-board change counts.

Open each board from its own folder so its matching `.kicad_pro` and `fp-lib-table` are used. The shared mux footprint is in `../../Symm60HE_Project.pretty/` relative to this README.
