# Fixed-layout production panels

Each child directory is one self-contained combined electrical project with a
single panel PCB, combined namespaced schematic, captured symbol library and
KiCad project file. Open and manufacture the `*-Panel` project; the retained
`*-Left.kicad_pcb` and `*-Right.kicad_pcb` files are mechanical/migration
inputs rather than separate electrical projects.

The eight directories cover every combination of:

- two 1.5u or three 1u keys on the left bottom row;
- standard or arrow-cluster right bottom row; and
- split or 2u Backspace.

Run `tools/layouts/verify_layout_panels.py` to verify combined schematic/PCB
parity, L/R namespace isolation, FN40HE Hall keepouts, panel dimensions,
mouse-bite rows, tooling holes and fiducials. Matching plate files use the same
directory/layout stem under `plate/`.
