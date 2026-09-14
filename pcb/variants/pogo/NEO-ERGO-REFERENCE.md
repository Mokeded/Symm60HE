# Neo Ergo daughterboard: photographic reference

The `pogo-neo` variant copies the Qwertykeys Neo Ergo interconnect topology.
This file records what the published photographs actually show, so the claims
in `CONNECTOR-AND-TENTING.md` can be traced to a source instead of to memory.

The Neo Ergo is a commercial product of Qwertykeys. Nothing here is derived
from its CAD; the observations below are read off published photographs, the
same method `../../../NOTICE.md` records for the DOE layout. The photographs
themselves are Qwertykeys' and are **not** vendored in this repository — the
source URLs below are the reference.

## Sources

- Official Qwertykeys Neo Ergo Build Guide (Notion):
  <https://qwertykeys.notion.site/Neo-Ergo-Build-Guide-db220293677346258479350f9102843f>
  — section 5, "How to change the daughterboard", and section 3, "Build".
- Divinikey's index page for the same guide:
  <https://help.divinikey.com/support/solutions/articles/63000288306-neo-ergo-build-guide>
- Product page (kernel/battery/daughterboard description):
  <https://www.qwertykeys.com/products/neo-ergo>

Retrieved 2026-09-14. Frames are cited by the guide's own file names.

## What the photographs show

| Frame | Guide step | Reading |
|---|---|---|
| `IMG_3514.heic` | 5, "another screw under the middle bracket" | Kernel top face, both pogo modules seated and protruding. Each is a black oval housing with a **2 × 8 gold spring-contact array** and one round magnet at each end of the field. The two modules sit side by side, mirrored, straddling the centreline. |
| `IMG_2748.heic` | 5, "unscrew these eight screws" | Kernel underside. A gold retaining bracket runs the full length of the centre and clamps over both module bodies; the USB-C port and the battery toggle `SW2` sit above it. The bracket, not the daughterboard, holds the modules. |
| `IMG_2749.heic` | 5, "remove the three screws" | Daughterboard in the kernel tray: a small white PCB carrying the MCU, held by three screws, with the two 2200 mAh cells either side of it. The module bodies protrude through the tray below it. |
| `IMG_2753.heic` | 5, "unclip and remove the magnetic connectors" | Daughterboard front face. Two side-by-side **FPC/ZIF connectors** are the module interface; each module's flex pigtail lands in one. Two further small white JST-style connectors at the outboard edges take the cells. |
| `IMG_2751.heic` | 5, "connect the batteries" | Both modules hanging off the daughterboard on short flex pigtails, with the cells wired in. Confirms the modules are separate replaceable assemblies, not part of the daughterboard. |
| `IMG_2620.heic` | 3, "find the PCB from the carrying case" | Bare PCB halves. At each half's centre-facing edge is a **2 × 8 tinned pad field** with a square pin-1 pad — the receptacle footprint before the part is fitted. |
| `IMG_2634.heic` | 3, "install the gaskets" | Populated halves, underside. The receptacle **is** fitted here: the same black oval housing, flat contacts, magnet at each end, soldered to the bottom face at the centre-facing edge. |
| `IMG_2633.heic` | 3, "flip the bottom case over" | Kernel installed in the bottom case, modules facing up. This is the surface the main PCB drops onto — no cable crosses the split. |

## Consequences for `pogo-neo`

1. **Contact count.** The Neo Ergo pair is 16 contacts in a 2 × 8 array, not
   the 2 × 7 previously recorded. `CONNECTOR-AND-TENTING.md` is corrected.
   This does not change our own design: the Symm60HE link needs 12 conductors
   and uses a catalogue Mill-Max `854`/`856` 1 × 12 pair.
2. **Topology confirmed.** Flat daughterboard, two identical replaceable
   modules on flex pigtails into ZIF connectors, main PCB mating directly
   through a soldered receptacle with no target-side cable. Every row of the
   comparison table holds.
3. **Retention is mechanical.** The gold bracket in `IMG_2748.heic` clamps the
   module bodies to the kernel; the magnets sit at the ends of the contact
   field and register the mate. This supports the existing rule that positive
   retention, not magnetic force, sets our stack.
4. **Magnet policy unchanged.** The Neo Ergo has no Hall sensors, so its
   magnets cost it nothing. Ours stay DNP until an assembled Hall-offset and
   noise test passes.

No part number is published for either half of the Neo Ergo connector, and
none was found. It remains a custom OEM part.
