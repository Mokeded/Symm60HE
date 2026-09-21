# Symm60HE wklbs2arrows layout-specific PCB pair

Generated from the universal routed master by `tools/make_layout_pcbs.py`.
The universal source boards are not modified.

- Left active Hall positions: 31
- Right active Hall positions: 31
- Left bottom row: three-key
- Right bottom row: arrows
- Backspace: 2u
- Removed left RGB footprints: none
- Removed right RGB footprints: DR21, DR4, DR5
- Board thickness remains 1.2 mm.
- The close bottom-row switch-alignment holes use their normal horizontal axis.
- Their LEDs use the standard 7.60 mm key-relative offset.
- The adjacent Shift stabilizer is turned so its smaller retention holes face
  those LED apertures; its key centre is unchanged.
- Mutually exclusive universal-layout LED apertures are removed with their
  unused RGB footprints.
- The retained Backspace and Shift-choice LEDs return to their ordinary row
  alignment; the 2U Backspace LED is horizontal.
- All four isolated M2 mounting holes retain the universal board coordinates,
  exactly matching every plate variant and clearing all switch/stabilizer cuts.

The daughterboard is common to all eight pairs and remains in `pcb/`.
After generation, finish one representative of each of the six unique halves,
run `tools/materialize_layout_permutations.py`, and then run
`tools/verify_layout_pcbs.py`. The checked-in DRC reports have zero routing or
connectivity errors and zero copper-edge warnings.
