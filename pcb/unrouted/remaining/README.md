# Remaining unrouted boards

This folder contains the 49 other PCB files from `pcb/`, including layout variants, panels, and accessory boards. The original WKL Left and Right boards are provided separately in `../wkl-fixed-layout/`.

Each `*-unrouted.kicad_pcb` has no copper tracks or vias. The mux footprint matches the uploaded WKL routing checkpoints, and shared mux, Hall sensor, and Hall capacitor placements are copied from those checkpoints. Existing translations between layout variants are preserved. Open each board from its own folder to use the accompanying KiCad project settings and footprint library table.

`manifest.csv` maps every output to its source and lists the counts of removed tracks/vias, updated muxes, matched placements, and retained copper zones.
