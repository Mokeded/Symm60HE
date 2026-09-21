# Symm60HE plate files

Manufacture the selected left/right pair from **1.5 mm POM**. This is the
project's locked nominal plate specification and matches the 1.5 mm plate
solids in the Fusion reference assembly. Ask the plate fabricator to preserve
the DXF dimensions without kerf compensation in the source file; compensation
belongs in the fabricator's cutting process.

Every keyboard uses one `-left.dxf` and one `-right.dxf`. The fixed-layout
pairs cover all eight independent combinations of left bottom row, right bottom
row, and Backspace type:

| Stem | Left bottom row | Right bottom row | Backspace |
|---|---|---|---|
| `Symm60HE-plate-wkl` | WKL, two 1.5u | Standard | Split 1u + 1u |
| `Symm60HE-plate-wkl-left-arrows-right` | WKL, two 1.5u | Arrows | Split 1u + 1u |
| `Symm60HE-plate-three-key-left-wkl-right` | Three 1u | Standard | Split 1u + 1u |
| `Symm60HE-plate-wklarrows` | Three 1u | Arrows | Split 1u + 1u |
| `Symm60HE-plate-wklbs2` | WKL, two 1.5u | Standard | 2u |
| `Symm60HE-plate-wkl-left-arrows-right-bs2` | WKL, two 1.5u | Arrows | 2u |
| `Symm60HE-plate-three-key-left-wkl-right-bs2` | Three 1u | Standard | 2u |
| `Symm60HE-plate-wklbs2arrows` | Three 1u | Arrows | 2u |

`Symm60HE-plate-universal-left.dxf` and
`Symm60HE-plate-universal-right.dxf` merge mutually exclusive switch openings
for the universal PCB.

All nine pairs follow the routed PCB Edge.Cuts along their top, bottom, and
stepped centre contours. The plate uses a uniform 0.15 mm outward allowance so
the larger plate apertures retain the project's 2.0 mm POM web target. Only the
side gasket regions depart from the PCB shape: each half has one continuous
straight outer gasket wall and one continuous straight centre-facing gasket
wall. Four smooth integral gasket-mount tongues
per half sit directly on those walls: two outer and two centre-facing. All eight
mounts use the same smooth 5 mm projection,
smooth, tapered tongue geometry as the last complete plate revision. Every
switch and stabilizer
opening is contained inside its plate outline. The narrowest finished web is
2.01 mm at the right split-backspace stabilizer; all other checked variants are
at or above that value.

Every PCB permutation has a correspondingly named
`Symm60HE-gasket-pads-<layout>.dxf` containing eight Poron pads matched to its
integral plate mounts. `Symm60HE-gasket-pads.dxf` remains as the universal
layout alias.

Every plate half has four 2.2 mm holes on `STANDOFF_HOLES`. Their coordinates
exactly match the four isolated NPTH mounting holes on the corresponding PCB
half in both the universal design and all eight fixed-layout designs. The
pattern was checked against every switch and stabilizer opening and each PCB's
component/trace geometry. The left and right patterns are intentionally not
mirrored because their FPC and multiplexer placement is asymmetric. Use M2
non-magnetic nylon spacers with a maximum 4.0 mm outside diameter; the DXFs
reserve that complete body plus at least 1.75 mm from all switch/stabilizer
openings and 2.0 mm from the plate edge.

Hype Keyboards publicly specifies 1.5 mm nominal plate thickness but does not
publish a numeric minimum-web rule. The 2.0 mm project rule is therefore a
conservative design target, not a quoted Hype limit; send these DXFs to Hype
for their final manufacturability review before ordering.

The plate has no flex-relief slots. This restores the continuous pre-flex-cut
structure between the switch, stabilizer and mounting openings. Do not add
relief cuts during CAM preparation.
