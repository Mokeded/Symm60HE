# Current build tooling

Run the supported pipeline from the repository root with `./build.sh`.

The retained tool set is deliberately limited to the current production
artifacts:

- `cad/`: PCB/plate preparation, populated reference export and verification.
- `generators/`: current schematic and Symm60HE firmware generation helpers.
- `layouts/`: the fixed-layout catalog and authoritative panel verifier.
- `pcb/`: deterministic preparation used by the ordinary ribbon-PCB build.
- `releases/`: universal, daughterboard and fixed-layout manufacturing packs.
- `mkplate.py`: all eight fixed-layout plate pairs plus the universal pair.
- `verify.py`: PCB, schematic, firmware, plate, manufacturing and 3D handoff
  checks.

Historical routing repair, experimental pogo, gallery-rendering and one-time
migration scripts are outside this current-build tree. The existing combined
panel projects are authoritative and are not regenerated from half boards by
an ordinary build.
