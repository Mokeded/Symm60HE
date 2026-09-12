# Symm60HE Fusion 360 case-design references

`Symm60HE-reference-assembly.step` is the primary Fusion 360 handoff. Import
it with **File > Open > Upload** and save the imported design as a Fusion
project, or run the `fusion-setup/Symm60HECaseSetup` script (see
`fusion-setup/README.md`) to build a named component tree from the individual
STEP files in one step. It contains nine separately named reference bodies:

- Left PCB
- Right PCB
- Daughterboard PCB
- Left universal plate
- Right universal plate
- Left switches
- Right switches
- Left keycaps
- Right keycaps

The two keyboard halves are shown at 6 degrees of tent and 11 degrees of
typing angle. Each PCB is 5 mm below its plate. There is deliberately no case
solid: build new top and bottom components around these reference bodies.

The switches and keycaps show the primary 60-key `doe-wkl` configuration, with
30 populated positions on each half. They are simplified mechanical envelopes,
not vendor-specific production models: switches use a 13.8 mm housing and MX
stem, while the keycaps use a tapered 1 mm-spacing envelope. Hide them for PCB
or plate work and show them to judge case-wall, blocker and typing clearances.
Set `SYMM60HE_VISUAL_LAYOUT` to `doe-wkl`, `doe-wklbs2`, `doe-wklarrows`, or
`doe-wklbs2arrows` before running `build.sh` to regenerate another populated
layout.

`Symm60HE-reference-assembly.FCStd` is the editable source assembly used to
create the STEP file. The individual STEP files are provided when importing
each reference as a separate Fusion component is preferable.

The previous case was removed from this directory. A hash-verified recovery
copy is retained under `work/recovery-case-20260911-0837/`.

`tenting-solution/` contains a separate editable 27-body fixed 6 degree
pogo/controller mechanism. It is intentionally independent from the empty
case-design reference assembly so it can be inserted, repositioned, or omitted
as one subsystem while the enclosure is modeled around the real PCBs and
plates.
