# Symm60HE

Symmetrical Hall effect Alice keyboard based off of the Doe — split into three
boards linked by ribbon cable.

GPLv3. Derived from FN40HE; see `NOTICE.md` for what is taken and from where.
The layout is a reconstruction of the DOE 60% by hare works, measured from
published photographs — not affiliated with that project.

Current manufacturing renders are in [`docs/img/`](docs/img/), including the
two-half panel, both sides of the compact daughterboard, and a populated Fusion
reference preview. The previous case was retired; the current case-design
handoff is a nine-body Fusion-compatible reference assembly.

The DOE 60% filled-WKL layout, built the way FN40HE is built (MT9102ET Hall
sensors, 8:1 analog muxes into an AT32F405RCT7) but cut into three boards linked
by ribbon cable:

| Board | Size | Carries |
|---|---|---|
| `pcb/Symm60HE-Left.kicad_pcb` | **158.9 × 107.7 mm** | 33 switch positions, 4 muxes, 1 ribbon link |
| `pcb/Symm60HE-Right.kicad_pcb` | **158.9 × 107.7 mm** | 36 switch positions, 4 muxes, 1 ribbon link |
| `pcb/Symm60HE-Panel.kicad_pcb` | **175.32 × 233.91 mm** | Stacked connected manufacturing panel containing both keyboard halves |
| `pcb/Symm60HE-Daughterboard.kicad_pcb` | **57 × 28 mm** | MCU, USB-C, ESD, both LDOs, crystal, BOOT/RESET, 2 outward-facing ribbon links |

Open each `.kicad_pro` in KiCad 10.

## Why the analog stays on the halves

Splitting a Hall-effect board is not like splitting a matrix board: the sensor
outputs are analog, and analog does not enjoy a ribbon cable. So each half keeps
its own four muxes and only **four already-multiplexed analog lines** cross to
the daughterboard, each with a ground beside it. That is 8 analog lines into 8
ADC inputs in total — the same architecture and the same firmware shape as
FN40HE, which also runs 8 muxes into A3, A4, A5, A6, A7, C4, C5, B0.

The mux address lines are broadcast to both halves, so both scan in lockstep.
The inhibit pin is tied to ground locally on each half, exactly as FN40HE does,
which is why no enable line crosses the ribbon.

The half-board FFC cable entries are mechanically mirrored: JL1 is at 270° and
JR1 is at 90°, so each flex can leave toward the centre without folding back
over its connector. Rotating JL1 reverses its numbered pad order relative to
the daughterboard; the left cable therefore maps daughter pin `N` to JL1 pin
`13-N`. The right cable remains pin-for-pin. The authoritative mapping is
`Symm60HE-ribbon-pinout.csv`.

The four board connectors are locked to BOOMELE `1.0-12P` / LCSC `C20111`:
12 positions, 1.0 mm pitch, top contact, right-angle SMD, for 0.3 mm FFC. Use
two JXTCONN `FC-1012P-100T3` / LCSC `C37635129` 10 cm same-side cables. Confirm
pin 1 through pin 12 with a continuity meter before the first powered assembly.

The two daughterboard cable mouths now face away from the MCU and toward their
respective case sides. Their routed signal-pad centers did not move: each body
was rotated 180 degrees, the numbered net order was reversed to preserve the
physical conductor order, and the board grew only 1 mm at each short side to
contain the complete manufacturer hold-down lands. This removes the avoidable
90-degree flex turn at the daughterboard.

## Magnetic pogo alternate

`pcb/variants/pogo-neo/` now contains the recommended 12-contact,
power-off-only alternate using
the orderable Mill-Max `854-22-012-30-004101` single-row SMT spring connector
and matching `856-10-012-30-051000` gold target. Twelve contacts carry every
existing FFC conductor without unused or redundant positions.

The 57 x 28 mm controller remains flat and rigid, oriented left-to-right under
the centre blocker so USB-C faces the rear wall. Each side uses a separate
20 x 6 mm replaceable spring head in a
captured but floating 3 degree kernel aperture. One short 12-way FFC connects
each head to the controller. The matching target is mounted directly on its
Hall PCB; there is no target module or second FFC. The plates carry only the
eight side gasket tabs. Magnets
remain retention-only and DNP until an assembled Hall offset/noise test passes.

The detailed fixed-angle mechanism is in `case/fusion360/tenting-solution/`.
It adds a 1.2 mm-floor central controller tray, mirrored 3 degree spring trays,
direct Hall-PCB target references, 0.4 mm-per-side floating apertures, capture
lips, asymmetric perimeter keys, compression stops, short-FFC envelopes, and
optional DNP magnet envelopes. Both assembled and exploded renders are under
`docs/img/24-*` and `docs/img/25-*`; the routed modules are in `docs/img/28-*`.

All five Neo-style boards report zero DRC violations and zero unconnected pads.
The existing FFC keyboard remains the checked production candidate until the
connector coupon, FFC motion, gasket motion, and Hall-noise tests pass. See
`pcb/variants/pogo-neo/README.md` and the coupon gate under
`pcb/variants/pogo/CONNECTOR-AND-TENTING.md`.

The pogo variant's layout-specific BOM/CPL package is under
`release/jlcpcb-pogo-neo/`. Its Fusion-importable example carrier is under
`case/fusion360/pogo-neo-mounting-reference/`; use the assembled STEP as the
case-design reference and the exploded STEP to inspect the retention stack.

A separate PCBWay RFQ/manufacturing package is under
`release/pcbway-pogo-neo/`, with a distributable archive at
`release/Symm60HE-PCBWay-Pogo-Neo.zip`. It contains both connected
family-panel orders, individual-board fallbacks, Gerbers, separated PTH/NPTH
drills, DRC reports, assembly/fabrication drawings, layout-specific PCBWay BOM
and centroid pairs, fabrication specifications, critical-connector placement
data, source boards, a manifest, and SHA-256 checksums. The two exact Mill-Max
pogo connector MPNs are marked **no substitution** and may be quoted as PCBWay
turnkey parts or supplied by the customer. This is independent of—and does not
replace or modify—the JLC release.

The two PCB Edge.Cuts contours are also exact reflections about the 151.209 mm
tent axis. Because the universal right half contains several alternative-layout
positions that the left does not, the common symmetric contour is the union of
both required envelopes rather than the smaller intersection: neither side
loses material needed by a switch, stabilizer, connector or mounting hole. The
source-board contours meet at the tent axis in assembled coordinates; the
manufacturing panel translates the right half 2 mm to create its routed slot.

## Layout options on one PCB

The boards carry **70 mechanical switch positions** so a single pair of PCBs
covers all four layouts from the published layout page plus normal and stepped
1.75u Caps Lock. Mutually exclusive positions share a mux channel, the way the
FN40HE BOM shares parts across its DNP columns:

- number row outer 2u — `=` + `]`, or one 2u backspace
- row 4 outer 2.25u — one shift, or ↑ + 1.25u shift
- bottom row outer 3u, each half — two 1.5u, or three 1u (`←↓→` on the right)

The 4.7625 mm close alternatives use one Hall sensor at their exact midpoint:
normal/stepped Caps Lock, left `SWL27/SWL28`, and right `SWR30/SWR31`. Both
mechanical switch openings remain, but only the midpoint MT9102ET and one
capacitor pair are assembled. The wider 9.525 mm and 14.2875 mm alternatives
remain separate populate-one sensor positions on a shared logical channel; do
not fit both sensors in one of those pairs.

Left needs 31 channels, right 32; four muxes give 32 each.

## Plate

`plate/` holds an **independent left/right DXF pair** for every layout plus an
independent universal pair. There is no rigid centre bridge: each plate half
follows its PCB and its own 3° tent plane. Mutually exclusive switch positions
overlap, so a fixed-layout pair picks one layout while the universal pair merges
the overlapping openings into durable slots. Every switch opening remains
inside its plate half; the narrowest edge web is 2.75 mm on the right half and
4.64 mm on the left half. The daughterboard mounts independently to the
case and is not carried by either plate.

The PCB halves retain their stepped, keymap-following outer contours. The plate
halves retain the key-field shape along their top and bottom edges, but use
continuous straight walls on both the outside and centre-facing sides. Those
walls stop at the real sloped top/bottom contours rather than extending into
rectangular end tabs, and every gasket tongue is the outermost feature on its
side. All eight tongues now use a Neo-Ergo-inspired long side-bearing profile:
24.0 mm overall length, a 20.0 x 4.0 mm Poron bearing area, 2.0 mm smooth end
transitions and 4.0 mm exposed projection. Two pads fit end-to-end in one of
the user's 80 x 4 x 3 mm gasket strips. The complete left and right moving
assemblies are spread 2.75 mm outward per side so the equal-size inner tongues
retain clearance without changing the pogo connection geometry. The
completed plate exterior, including the centre-wall corners and
integral gasket tongues, uses a 1.0 mm material-side radius. Switch and
stabilizer openings remain dimensionally unchanged. Only the selected
bottom-row U recess on each
half is structurally filled. Its visual shape remains in the removable case
top, which overlaps the plate by 3.0 mm around the recess. The obsolete right
plate daughterboard carrier and its two holes have been removed.

The controller daughterboard's rear edge is locally set back 1.0 mm beneath
J1 across a 14 mm-wide opening, so the actual USB-C shell overhangs the PCB
while retaining its routed footprint position.

The fabrication names end in `-left.dxf` and `-right.dxf`; both files are needed
for one keyboard. Files without a side suffix are obsolete one-piece previews
and must not be sent for fabrication.

`plate/Symm60HE-gasket-pads.dxf` contains eight discrete side pads: four
outer/corner positions and four beside the centre kernel. They attach only
to integral plate tabs with curved, tapered roots; there are no square shoulder
steps, top/bottom gasket tabs, or gasket features on either Hall PCB. Use
20 mm lengths cut from the 80 x 4 x 3 mm gasket strips.

## Fusion 360 case-design reference

The previous generated case solids were removed from the active project. Import
`case/fusion360/Symm60HE-reference-assembly.step` into Fusion 360 and build the
case around its nine separately named reference bodies:

- left PCB and left universal plate
- right PCB and right universal plate
- compact daughterboard PCB
- XVX Whisper EC/HE-specific left/right switch clearance banks
- row-specific Cherry-profile keycap banks for the primary 60-key `doe-wkl`
  layout

The two plate/PCB pairs are positioned at 3° lateral tent and 7° front-to-back
typing angle, with each PCB 5 mm below its plate. No case solid is included by
design. The switch and keycap bodies are visualization/clearance envelopes and
can be hidden independently. XVX does not publish mechanical CAD for the
Whisper, so that body records the named product's published features but is not
manufacturer CAD. The keycaps follow the open KeyV2 Cherry R1-R4 dimensions;
they are not exact kit/manufacturer production models. Individual STEP files
make it easy to import each reference
as its own Fusion component; `Symm60HE-reference-assembly.FCStd` is the editable
source assembly. See `case/fusion360/README.md`.

The retired case is preserved, with hashes, under
`work/recovery-case-20260911-0837/` in case any geometry needs to be recovered.

## Routing

Two copper layers, and a design rule picked so that the router's own grid
enforces it: **0.2 mm traces, 0.15 mm clearance, 0.60/0.30 mm vias**. That is a
relaxed spec for any fabricator — 0.127/0.127 is the usual floor — and it is
what lets nets on cells 0.5 mm apart sit beside each other without a separate
spacing pass. Grid cells are 0.5 mm apart orthogonally and 0.354 mm diagonally,
and 0.2 + 0.15 = 0.35 mm fits inside the smaller of those.

Every component on the halves sits on the back. The completed signal routing
uses both external copper layers. **+3V3A is explicit routed copper**, while GND
is poured on both F.Cu and B.Cu. The compact daughterboard deliberately remains
mixed-side to minimize its outline; it also uses explicit power routing and GND
pours on both external layers. There are no internal copper layers.

| | Left | Right | Daughterboard |
|---|---|---|---|
| Connections | fully connected | fully connected | fully connected |
| Segments | 1070 | 1241 | 405 |
| Vias | 98 | 132 | 37 |
| Signal copper | F.Cu + B.Cu | F.Cu + B.Cu | F.Cu + B.Cu |
| F.Cu pour | GND | GND | GND |
| B.Cu pour | GND | GND | GND |

### Explicit analog rail and dual GND pours

The current manufacturing design uses routed +3V3A rather than treating an
entire copper side as the analog supply. This leaves both sides available for
GND pours around the two-layer signal routing and makes the power path explicit
in the board connectivity. Existing stitching vias join the two ground layers
and isolated regions. KiCad refills the pours during DRC and release generation.

### Three things in the router that were bugs first

**A diagonal step needs both of its orthogonal neighbours.** Otherwise two nets
cut the same gap from opposite corners and cross. Cell ownership cannot see it —
neither net owns a cell the other used — and it showed up as 49 shorts on the
left half alone. Requiring both neighbours rules out the corner cut and the
crossing together, because the other net's diagonal owns exactly those two cells.

**Fine-pitch pins are met head-on, never from the side.** A 0.65 mm TSSOP leaves
0.25 mm between pads and a 0.5 mm LQFP leaves 0.2 mm; no trace fits between them
at any sane rule. So each pad owns a private lane along its own axis, only as
wide as the pad itself, and the maze starts from a fan-out point at the end of
it — staggered near/far by pin parity, so neighbouring escape points land on a
diagonal instead of at pin pitch. Without the lane a pin has no way out at all:
its two neighbours' keep-out margins meet in front of its tip and whichever was
blocked first owns the only cells it could have escaped through. The lane runs
**both ways**, because outwards is not always the useful direction — an edge
connector's contacts face off-board, since that is the way the cable goes in, so
its only exit is inwards under its own body.

**Nothing is written that cannot be proved.** Once a path is found it is rebuilt
as real geometry and checked against every pad, trace and via already down. If
it violates clearance it is thrown away and the next way onto the pad is tried;
if all of them fail the connection is left unrouted and counted. The boards on
disk are therefore clean by construction, and the honest number is the split in
the table rather than a segment count.

Nets are routed shortest-span first, which is greedy: an early net can wall off
a later one for no better reason than that it was shorter. There is no rip-up,
so instead the order is reshuffled a few times and the best result kept.

Drilled holes count as obstacles **even when they belong to a switch position
your layout does not populate** — the hole is there either way, which is a trap
specific to a multi-layout board. Chaining the analog rail sensor-to-sensor was
the first attempt at it and was wrong for the same reason: a straight line
between two sensors' VCC pads runs through the MX leg holes between them.

### Meeting a pad in the middle

Worth its own note, because it cost more connections than anything else. Each
pad offers the router a list of ways to be met — the escape points along its
axis, and the bare pad centre — tried in order and capped, since each one costs
a maze search. The pad centre was first on that list.

It should have been last. Meeting a pad in its middle lets the maze leave
sideways, and on a 0.5 mm pitch package sideways means straight across the
neighbouring pin, so every one of those routes was found and then thrown out by
the clearance check. Twelve dead candidates per pad, and the escapes along the
pad's own axis — the ones that work — were never reached. Moving the pad centre
to the end of the list took the daughterboard from 10 routed to 27, without
changing a single trace rule.

### The daughterboard

It is the hard one: an LQFP-64 on 0.5 mm pitch, two 12-way ribbons and a USB-C
receptacle. Three changes made it routable at all:

- **The pin assignment is FN40HE's**, read off its board — not invented here.
  See `NOTICE.md`.
- **The board is a compact 57 × 28 mm.** It includes two M2 NPTH mounting holes
  so a small bracket can attach it to the plate without hard-mounting either
  keyboard half.
- **The USB-C receptacle moved off the centre line**, 10.5 mm right, to sit
  beside the MCU's USB pins rather than diagonally across the board from them.
  The case cutout follows the same offset — both come from `USB_X_OFF` in
  `tools/outline.py`.

The daughterboard is fully connected. Its two 12-way ribbon connectors remain
the densest part of the layout because their contacts escape inward beneath the
connector bodies. A no-reroute outline search found 57 × 28 mm clean;
shrinking the existing outline produced copper-to-edge violations.
Going smaller therefore requires moving parts and rerouting, with no guarantee
that the existing two-sided density can be retained.

## Building and checking

```sh
./build.sh          # rebuild panel, Fusion references, release and all checks
tools/verify.py     # just the checks
```

`verify.py` exits non-zero on any failure, so it works in CI.

Native KiCad connectivity-capture schematics sit beside all three boards. They
were generated from every connected PCB pad, and `tools/schematic_parity.py`
checks each reference/pad/net tuple before ERC. The custom symbol pins are
passive because this board-first reconstruction does not invent electrical pin
types; ERC therefore proves schematic connectivity integrity, while the parity
and net checks prove agreement with the routed boards.

## Firmware

`firmware/libhmk/keyboards/symm60he/keyboard.json` is the Symm60HE target. It
maps all 63 logical channels through AML1-AML4 and AMR1-AMR4, exposes all 69
physical switch positions with split-backspace and WKL/arrows options, and
retains libhmk's rapid trigger, adjustable actuation, SOCD/advanced keys, four
profiles, calibration and web-configurator support.

The checked release binary is `firmware/build/firmware.bin`. To rebuild, install
the root requirements, run `python setup.py -k symm60he` in `firmware/libhmk`,
then `pio run -e symm60he`. A path without spaces is currently required by the
upstream link-map build step. Put the board in DFU mode with BOOT held while
resetting, install `dfu-util`, and run `pio run -e symm60he -t upload`.

## Manufacturing release

`release/jlcpcb/` contains two manufacturing orders:

- `Symm60HE-Half-Panel-Gerbers.zip`: both keyboard halves in one connected
  175.32 × 233.91 mm stacked panel, with thirteen five-hole mouse-bite rows at
  0.75 mm pitch, three B.Cu global fiducials, four 2 mm tooling holes, and all
  SMT parts on B.Cu
- `Symm60HE-Daughterboard-Gerbers.zip`: the separate compact, mixed-side
  daughterboard order, with three local fiducials on each assembly side

Both are 2-layer, 1.2 mm designs. The generated BOMs contain only fitted SMT
parts and every line has an exact LCSC assignment; plated mounting holes and
other board-only features are omitted. The universal half-panel has four
matched, mutually exclusive BOM/CPL pairs under
`release/jlcpcb/Symm60HE-Half-Panel/layouts/`; choose exactly one layout and do
not create an all-positions placement list. Inspect both ZIPs in JLC's Gerber
viewer before payment.

## What has been checked, and what has not

Checked against the current files:

- KiCad 10.0.5 refilled every zone, then reported **zero DRC violations and
  zero unconnected items** on all three source boards and the two-half panel
- net audit clean: every channel reaches exactly one mux input, one sensor and
  its decoupling; the address lines reach all four muxes and the ribbon; each
  ADC net reaches the MCU and one ribbon
- every board declares only `F.Cu` and `B.Cu`; +3V3A is routed and GND is
  poured on both sides
- all plate and gasket DXFs parse with zero `ezdxf` audit errors
- the Fusion reference assembly contains nine finite, separately named bodies
- all three native schematics pass KiCad ERC with zero messages, and their 786
  connected reference/pad/net assignments match the PCBs exactly
- the Symm60HE libhmk firmware compiles successfully for AT32F405RCT7; the
  current image uses 33,500 bytes of flash and 13,884 bytes of RAM
- both fabrication ZIPs pass archive integrity checks and include both
  copper layers, masks, clipped silkscreens, Edge.Cuts, PTH and NPTH drills
- every normally ignored DRC rule was re-enabled in temporary projects; see
  `release/reports/ignored-drc-audit.md` and its raw reports

Still required before committing to a production quantity:

- confirm the right board's one tangent pair of NPTH holes in JLC's Gerber
  viewer. They belong to mutually exclusive up-arrow and 2.25u-shift/stabilizer
  positions on the universal PCB; use a layout-specific PCB if JLC rejects the
  resulting merged/tangent drill geometry
- print or machine a fit-check prototype for the case, split plates,
  daughterboard bracket, USB opening, gaskets, ribbon bends and fasteners
- electrically prototype the Hall-sensor noise margin and ribbon-link behavior;
  CAD connectivity and DRC cannot prove analog performance

The mux intentionally uses SOIC-16 rather than FN40HE's TSSOP-16 — the same
chip in a larger package, for the routing-clearance reason given in `NOTICE.md`.

## Files

- `Symm60HE-switch-map.csv` — every logical-layout switch position, mm, rotation, and build
- `Symm60HE-sensor-aliases.csv` — close alternate positions that use a shared midpoint sensor
- `Symm60HE-channel-map.csv` — sensor → mux → channel, per half
- `Symm60HE-ribbon-pinout.csv` — the 12-way link
- `pcb/variants/pogo/Symm60HE-pogo16-pinout.csv` — the proposed 16-contact
  power-off-only compression link
- `Symm60HE-BOM.csv` — both halves and the daughterboard
- `docs/img/` — PCB, split-plate, two-half-panel and compact-daughterboard
  renders
- `tools/` — generators and checkers; `build.sh` runs them in order
- `Symm60HE_Project.pretty/` — the footprint library, local and portable

Rotation convention: KLE's `r` is a standard-matrix rotation in a y-down frame,
so it applies as `+r` when drawing. The boards store `-r`, because KiCad's `at`
angle is counter-clockwise-positive on screen. Reading the boards back with
`-angle` reproduces the KLE tiling to 20.0 mm² of wedge sliver, against 125.6 mm²
the other way round — `tools/img.py` now asserts that the key outlines tile, so
getting this backwards fails loudly instead of quietly producing a mirrored
picture.

The key footprints are derived from FN40HE's verified HE1 footprint, so the
sensor pads, the MX leg holes and the plate cutout are the shapes that already
passed DRC there; only the cap outline is rescaled per width.

## Bottom-side population, and why the boards are small

Everything on the halves sits on the **back** copper, as FN40HE does — sensors,
decouplers, muxes and the ribbon connector. Only the NPTH parts (stabilisers and
M2 holes) stay layer-agnostic on the front.

That is what makes the boards small. With parts on the front they need a bezel
band to live in, so the outline had to follow the case. On the back they hide
under the switches — the underside of a key cell is free except for the sensor,
the two MX leg holes and any stabiliser holes — so the outline can hug the key
field with a 2 mm rim instead:

| | Before | Now | |
|---|---|---|---|
| Left | 163.5 × 115.8 mm, 183.7 cm² | **158.9 × 107.7 mm** | symmetric compact envelope |
| Right | 161.1 × 115.8 mm, 181.0 cm² | **158.9 × 107.7 mm** | mirrored symmetric envelope |

The outline is the convex hull of that half's key cells plus a 2 mm rim, unioned
with the stabiliser holes and their own rim — the spacebar's lower stabiliser
hole reaches 10.25 mm below the cell and gets clipped by a plain hull otherwise —
then trimmed to the case interior and cut at the centre line with a 2 mm gap.

The flip is not hand-rolled: `tools/flip.py` mirrors y, swaps F.* layers for
B.*, and sets each placed pad's angle to its library angle plus the footprint
rotation. That rule was read off FN40HE's own flipped footprints, and flipping
our 1u key footprint at −90° reproduces FN40HE's placed HE16 exactly — same pad
coordinates, same angles, same layers.

## Licence

GPLv3, because this derives from FN40HE which is GPLv3. See `LICENSE` and
`NOTICE.md`. Retain source, licence and attribution when redistributing.
