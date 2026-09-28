# WKL fixed-layout unrouted boards

These are routing starters for the fixed WKL layout pair:

- `Left/Symm60HE-wkl-Left-unrouted.kicad_pcb`
- `Right/Symm60HE-wkl-Right-unrouted.kicad_pcb`

They were made from the current routing checkpoints `WKL-Left-42-adc-deepsearch-checkpoint` and `WKL-Right-75-adc-r1-direct-f-trunk` on 2026-09-27. All copper track segments and vias were removed. Component footprints and placements, including the mux footprint and Hall-effect capacitor changes, board geometry, and nets were retained. These checkpoints contain no copper zones.

Each board folder includes its matching KiCad project settings and footprint library table. These are unrouted routing starters; expect open connections until you route them.
