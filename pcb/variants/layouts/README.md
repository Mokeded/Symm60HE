# Symm60HE fixed-layout PCB permutations

These eight PCB pairs cover every permutation of the three independent
physical choices represented in `Symm60HE-switch-map.csv`:

| Directory | Left bottom row | Right bottom row | Backspace |
|---|---|---|---|
| `wkl` | WKL, two 1.5u keys | Standard, no arrows | Split 1u + 1u |
| `wkl-left-arrows-right` | WKL, two 1.5u keys | Arrow cluster | Split 1u + 1u |
| `three-key-left-wkl-right` | Three 1u keys | Standard, no arrows | Split 1u + 1u |
| `wklarrows` | Three 1u keys | Arrow cluster | Split 1u + 1u |
| `wklbs2` | WKL, two 1.5u keys | Standard, no arrows | 2u |
| `wkl-left-arrows-right-bs2` | WKL, two 1.5u keys | Arrow cluster | 2u |
| `three-key-left-wkl-right-bs2` | Three 1u keys | Standard, no arrows | 2u |
| `wklbs2arrows` | Three 1u keys | Arrow cluster | 2u |

Each directory contains independent left and right KiCad PCB/project files, a
KiCad DRC report for each half, and a layout-specific README. All sixteen PCB
halves are 1.2 mm designs with only the selected Hall sensors, LEDs, alignment
holes, and stabilizers retained.

The eight pairs are assembled from six unique verified halves: two left-bottom
options and four right-side combinations. `tools/materialize_layout_permutations.py`
copies those verified representatives into every named pair so electrically
identical halves cannot drift between permutations.
