# Attribution

This project is derived from **FN40HE** by Mokeded, which is GPLv3-licensed
hardware design work. It is therefore distributed under the GPLv3 as well; see
`LICENSE`.

What is taken from FN40HE, and how:

| Here | From FN40HE | How |
|---|---|---|
| `Symm60HE_Project.pretty/HE_KEY_*.kicad_mod` | `HE1_MT9102ET_Key_1.00u.kicad_mod` | derived — sensor pads, MX leg holes and plate cutout kept verbatim, only the cap outline rescaled per width |
| `Symm60HE_Project.pretty/STABILIZER_MX_2U`, `MountingHole_2.2mm_M2_Pad`, `U1`–`U4`, `Y1`, `SW1`, `C1`, `C2`, `C148`, `R3`, `F1` | same files | copied verbatim |
| `Symm60HE_Project.pretty/AM1_SOIC-16…` | replaces FN40HE's `AM1_TSSOP-16…` | **not** copied. Same chip, SN74LV4051A**D** instead of ...**APWR**: TSSOP's 0.65 mm pitch leaves 0.25 mm between pads, which no trace clears, so every interior mux pin was unroutable. SOIC's 1.27 mm pitch leaves 0.67 mm |
| board `(setup)` / `(layers)` block in each `.kicad_pcb` | `FN40HE.kicad_pcb` | copied, so design rules and stackup match |
| AT32F405RCT7 pin assignment | `FN40HE.kicad_pcb` U4 | read off the working board rather than from a datasheet: crystal on 5/6, reset on 7, mux selects on 9/10/11, analog rail on 13, the eight multiplexed inputs on 17 and 20–26, USB and its reference resistor on 33/34/35, SWD on 46/49/55, boot on 60. The daughterboard's parts are placed to suit it |
| Analog rail as a pour of its own, alongside GND | FN40HE's `+3.3VA` zone | same idea; here it goes on F.Cu, which is free because the halves are populated on the back |
| Mux architecture — 8× SN74LV4051A into 8 ADC inputs, INH tied low | FN40HE | same approach, re-derived for a split board |
| Cherry PCB-mount stabiliser hole pattern | `S1_STABILIZER_HOLES` | measured from it |

The keyboard **layout** is a reconstruction of the DOE 60% by *hare works*, from
the geekhack interest check
([topic 126873](https://geekhack.org/index.php?topic=126873.0)) and photographs
posted there. No CAD or layout data from that project was used — the geometry
here was measured from published images and rebuilt. The DOE name refers to the
layout being reproduced; this project is not affiliated with or endorsed by its
designer.
