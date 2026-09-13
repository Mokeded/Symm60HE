# Symm60HE Neo-style floating-head pogo variant

This is the recommended pogo architecture. It does not bend a daughterboard or
use FR-4 as a living hinge.

## Electrical stack per side

1. The unchanged 57 x 28 mm controller uses its existing 12-way FFC connector.
2. One short, replaceable FFC reaches a 20 x 6 mm floating spring head carrying
   the 12-contact Mill-Max `854-22-012-30-004101` block.
3. The spring head sits in a captured 3 degree kernel aperture with 0.4 mm X/Y
   clearance per side; lips retain it without clamping it rigidly.
4. A matching Mill-Max `856-10-012-30-051000` target is mounted directly on
   the copied Hall PCB in place of its FFC connector.
5. There is no target daughterboard and no target-to-Hall-PCB FFC.

The 12 contacts are exactly the 12 existing ribbon conductors. Mating is
power-off only. Magnets remain DNP until an assembled Hall-offset/noise test
passes.

## Mechanical isolation

The target connector is soldered directly to its **Hall PCB**, following the
Neo Ergo mounting topology. The spring head is a replaceable connector module
captured loosely by the central kernel and plugs into the controller's ZIF
socket through one short FFC. Compression hard stops and the two apertures
control pogo compression without preventing gasket-following motion. This is
independent of the keyboard suspension: gasket load still enters only through
the plates.

The keyboard suspension is also plate-only: four outer side gasket pads plus
four centre-side pads, eight total. There are no top/bottom gasket tabs and no PCB
gasket tabs. This keeps case/gasket load out of the sensor board while allowing
each split plate to move independently.

Each compact module is a two-sided assembly: the Mill-Max spring row is on
F.Cu and the FFC connector is directly behind it on B.Cu. This removes the old
10 mm routing corridor and prevents the two floating boards from overlapping
at the 6.418 mm target-row separation. The module boards have no alignment
holes through their fanout; the case pockets must locate them from the 20 x 6
mm perimeter and retain them loosely enough to follow gasket motion.

## Files and status

- `Symm60HE-Neo-Controller.kicad_pcb`: generated copy of the checked controller
- `Symm60HE-Neo-*-SpringModule.kicad_pcb`: floating controller-side heads
- `Symm60HE-Neo-Left-Half.kicad_pcb`: left Hall PCB with direct target
- `Symm60HE-Neo-Right-Half.kicad_pcb`: right Hall PCB with direct target
- `Symm60HE-neo-pogo12-pinout.csv`: mating contact map
- `*-drc.rpt`: KiCad DRC evidence

All five boards currently report zero DRC violations and zero unconnected pads.
The original Hall-PCB outlines are retained; only the local FFC breakouts are
replaced in the variant copies. Physical fit, connector compression, FFC bend
radius, Hall noise, and typing-motion endurance still require a prototype.

Regenerate and check with:

```sh
./.venv/bin/python tools/make_neo_pogo.py
./.venv/bin/python tools/verify_neo_pogo.py
./.venv/bin/python tools/release_neo_pogo.py
```

## BOM and placement files

`release/jlcpcb-pogo-neo/` contains complete and JLCPCB-only BOM/CPL pairs for
all five active PCBs. The controller and two spring modules are common to every
build. Because the Hall PCBs carry mutually exclusive universal-layout switch
positions, their assembly files are separated into `doe-wkl`, `doe-wklarrows`,
`doe-wklbs2`, and `doe-wklbs2arrows` folders. Choose exactly one layout folder;
populating every sensor position at once is not valid.

Close 4.7625 mm alternatives are different: normal/stepped Caps Lock, left
`SWL27/SWL28`, and right `SWR30/SWR31` each use one sensor at the midpoint and
one capacitor pair. Their two switch openings are mechanical options, so the
same midpoint sensor appears in either applicable assembly selection. All
active rigid PCBs and spring modules are modelled and released at 1.2 mm.

The complete files retain the Mill-Max spring and target blocks. The matched
JLCPCB files omit those two non-LCSC parts and the hand-install list calls them
out explicitly. Confirm stock, substitutions, pin 1, layer, and rotation in the
assembler's placement viewer before ordering.

## Fusion mounting reference

`case/fusion360/Symm60HE-case-reference-assembly.step` is the authoritative
assembled reference. It includes the real 20 x 6 mm module boards, F.Cu spring
blocks, B.Cu FFC connector envelopes, direct Hall-PCB targets, flat controller,
and flexible cable envelopes in the keyboard's tented/typed coordinate system.
The previous detached 20 x 20 mm carrier demonstration is retired because it
cannot represent the current hardware or its centre-seam clearance.
