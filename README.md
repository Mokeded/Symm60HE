# Symm60HE

Symmetrical Hall effect Alice keyboard based off of the Doe — split into three
boards linked by ribbon cable.

GPLv3. Derived from FN40HE; see `NOTICE.md` for what is taken and from where.
The layout is a reconstruction of the DOE 60% by hare works, measured from
published photographs — not affiliated with that project.

## Browse the designs

The GitHub-facing [`designs/`](designs/) index groups the project by connection
system and physical layout while keeping one canonical copy of every large CAD
and fabrication file:

| Area | Contents | Status |
|---|---|---|
| [Ribbon cable](designs/ribbon/) | Current universal PCB and all fixed-layout PCB pairs | **Current manufacturing candidate** |
| [Pogo concepts](designs/pogo/) | Pogo16 coupon, Neo magnetic alternate and serpentine experiment | Prototype or archived; read each status before use |
| [Plates](designs/plates/) | Matching 1.5 mm POM plate and Poron gasket files | Current |
| [3D models](designs/3d-models/) | Populated ribbon assembly, component references and pogo mechanics | Current reference plus archived concepts |
| [Firmware](designs/firmware/) | Firmware source, binary and four universal-layout profiles | Current |

Start at [`designs/README.md`](designs/README.md) if you are browsing this
repository on GitHub. Manufacturing files are linked from the same hierarchy;
there are no duplicate Gerbers or CAD exports hidden behind the index.

Current manufacturing renders are in [`docs/img/`](docs/img/), including the
two-half panel, both sides of the compact daughterboard, and a populated Fusion
reference preview. The previous case was retired; the current case-design
handoff is a fourteen-body Fusion-compatible reference assembly with separately
controllable populated PCB component bodies.

The DOE 60% filled-WKL layout, built the way FN40HE is built (MT9102ET Hall
sensors, 8:1 analog muxes into an AT32F405RCT7) but cut into three boards linked
by ribbon cable:

| Board | Size | Carries |
|---|---|---|
| `pcb/Symm60HE-Left.kicad_pcb` | **158.9 × 107.7 mm** | 33 independent Hall positions, 5 muxes, 1 ribbon link |
| `pcb/Symm60HE-Right.kicad_pcb` | **158.9 × 107.7 mm** | 36 independent Hall positions, 5 muxes, 1 ribbon link |
| `pcb/Symm60HE-Panel.kicad_pcb` | **162.29 × 227.83 mm** | Stacked connected manufacturing panel containing both keyboard halves |
| `pcb/Symm60HE-Daughterboard.kicad_pcb` | **50 × 31 mm** | MCU, USB-C, ESD, both LDOs, crystal, BOOT/RESET, 2 outward-facing ribbon links and 4 perimeter M2 mounts |

Open each `.kicad_pro` in KiCad 10.

## Why the analog stays on the halves

Splitting a Hall-effect board is not like splitting a matrix board: the sensor
outputs are analog, and analog does not enjoy a ribbon cable. So each half keeps
five muxes and only **five already-multiplexed analog lines** cross to the
daughterboard. That is 10 analog lines into 10 ADC inputs in total. The fifth
mux on each half is what makes every alternate physical switch position
independently observable; firmware can disable unused positions without an
unselected Hall sensor sharing the active sensor's ADC channel.

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

## Archived magnetic pogo alternate — do not manufacture

`pcb/variants/pogo-neo/` contains a historical 12-contact, power-off-only
alternate using
the orderable Mill-Max `854-22-012-30-004101` single-row SMT spring connector
and matching `856-10-012-30-051000` gold target. Twelve contacts carry every
existing FFC conductor without unused or redundant positions.

The 57 x 28 mm controller remains flat and rigid, oriented lengthwise on the
centreline. Each side uses a separate 20 x 20 mm replaceable spring head in a
captured but floating 6 degree kernel aperture. One short 12-way FFC connects
each head to the controller. The matching target is mounted directly on its
Hall PCB; there is no target module or second FFC. The plates carry only the
eight equal short side gasket tabs: two mounts on each outer and centre-facing
plate edge. The interior pairs sit on the edge sections closest to the split.
Magnets
remain retention-only and DNP until an assembled Hall offset/noise test passes.

The detailed fixed-angle mechanism is in `case/fusion360/tenting-solution/`.
It adds a 1.2 mm-floor central controller tray, mirrored 6 degree spring trays,
direct Hall-PCB target references, 0.4 mm-per-side floating apertures, capture
lips, asymmetric perimeter keys, compression stops, short-FFC envelopes, and
optional DNP magnet envelopes. Both assembled and exploded renders are under
`docs/img/24-*` and `docs/img/25-*`; the routed modules are in `docs/img/28-*`.

The Neo generator predates the final outward-facing FFC placement and no longer
reconstructs valid target-board breakouts from the current production halves.
Its old source boards, renders and release folders are retained only as design
history: **do not order them**. They are deliberately excluded from
`build.sh`. The checked manufacturing candidate is the ordinary FFC-linked
keyboard described in this document. Any future pogo revision must be
rerouted for the complete current 12-conductor interface and independently
pass DRC, continuity, connector-coupon, FFC-motion, gasket-motion and Hall-noise
testing before its release folders are re-enabled.

The archived pogo variant's layout-specific BOM/CPL snapshot is under
`release/jlcpcb-pogo-neo/`. Its historical Fusion-importable example carrier is under
`case/fusion360/pogo-neo-mounting-reference/`; use the assembled STEP as the
case-design reference and the exploded STEP to inspect the retention stack.

A historical PCBWay RFQ package is under
`release/pcbway-pogo-neo/`, with a distributable archive at
`release/Symm60HE-PCBWay-Pogo-Neo.zip`. It contains both connected
family-panel orders, individual-board fallbacks, Gerbers, separated PTH/NPTH
drills, DRC reports, assembly/fabrication drawings, layout-specific PCBWay BOM
and centroid pairs, fabrication specifications, critical-connector placement
data, source boards, a manifest, and SHA-256 checksums. The two exact Mill-Max
pogo connector MPNs are marked **no substitution** and may be quoted as PCBWay
turnkey parts or supplied by the customer. These archived files are not tied to
the current production PCB sources and must not be submitted for manufacture.

The two PCB Edge.Cuts contours are also exact reflections about the 151.209 mm
tent axis. Because the universal right half contains several alternative-layout
positions that the left does not, the common symmetric contour is the union of
both required envelopes rather than the smaller intersection: neither side
loses material needed by a switch, stabilizer, connector or mounting hole. The
source-board contours meet at the tent axis in assembled coordinates; the
manufacturing panel translates the right half 2 mm to create its routed slot.

## Layout options on one PCB

The boards carry **69 independently scanned Hall positions** so a single fully
populated pair can cover all four layouts from the published layout page. The
firmware profile selects the active physical positions before calibration and
scan processing; inactive sensors therefore cannot generate key events. The
alternatives are:

- number row outer 2u — `=` + `]`, or one 2u backspace
- row 4 outer 2.25u — one shift, or ↑ + 1.25u shift
- bottom row outer 3u, each half — two 1.5u, or three 1u (`←↓→` on the right)

All 33 left and 36 right sensors have separate mux inputs.

### Per-key lighting

Every populated position has a reverse-mount SK6812MINI-E on B.Cu shining up
through a 3.5 × 3.1 mm board aperture into the Gateron KS-20's "hole for
setting RGB": the case pocket that spans roughly 3.8–6.9 mm from the switch
centre on the cover's window side. The LED sits at **+5.35 mm along the key's
local Y**, i.e. on the south (user-facing) side of the key, so the light fills
the transparent cover and spills around the front of an opaque cap the way the
Wooting 60HE+ backlight does. Install every switch with its RGB pocket toward
the user; the plate cutout and the ±5.08 mm alignment pins are symmetric, so
the switch fits either way. With the 0.84 mm lens section of the 1.78 mm
package inside a 1.2 mm board the lens tip stays 0.36 mm below the switch
seating face.

A fixed-layout board restores its close-pair switches' alignment drills to the
ordinary horizontal axis and returns the compromise LEDs to the row, but only
where that space is actually free: where a key's own decoupling capacitor or a
stabiliser hole occupies it, the LED keeps the universal offset, and the
stabilisers themselves keep the master's angle now that the apertures face
south. Every generated half is audited against the pocket window rather than a
nominal offset, and all sixteen boards report zero DRC and connectivity errors.

The universal halves carry three compromises that the fixed-layout boards do
not: the four 4.7625 mm close bottom-row alternatives use vertical alignment
pins, so their switches sit rotated 90° and each pair shares one LED placed in
the side pocket of the primary WKL key (facing away from its alternate); the
`↑` position's aperture is pulled to 4.40 mm because the 2.25u Shift
stabiliser hole coexists under it; and the `=`, `]` and 1.25u-Shift apertures
are shifted 1.5 mm sideways for the same stabiliser holes. Both universal
halves report zero electrical, connectivity, mask, aperture, and
copper-to-edge DRC findings.

`pcb/variants/layouts/` contains eight generated PCB pairs covering every
permutation of the independent left-bottom-row, right-bottom-row, and
Backspace choices. The four historical names (`wkl`, `wklarrows`, `wklbs2`,
and `wklbs2arrows`) are retained, alongside four mixed-half variants. Each pair
removes inactive Hall footprints,
alignment holes, local sensor capacitors, layout-only stabilizers, and unused
RGB footprints. The close-pair alignment drills return to the normal horizontal
axis and the selected LEDs return to the standard +5.35 mm south-pocket offset.
The nearby Shift stabilizers are rotated 180 degrees so their smaller retention
holes face those apertures without changing the stabilizer or key centres.
Unused reverse-mount RGB footprints take their board apertures with them. The
retained Backspace and Shift-choice LEDs also return from their universal-board
clearance positions to the ordinary south-pocket position under their own
switch.
These derivatives are mechanically audited, but their locally changed LED
routing is audited after every regeneration: KiCad must report zero clearance,
short, crossing, dangling-track/via, connection-width, or unconnected-item
errors before a generated pair is accepted.

The four additional mixed-half directories are
`wkl-left-arrows-right`, `three-key-left-wkl-right`,
`wkl-left-arrows-right-bs2`, and `three-key-left-wkl-right-bs2`.
The six unique half designs are independently finished and DRC-checked, then
`tools/layouts/materialize_layout_permutations.py` copies those verified halves into
all eight named pairs.

## Plate

`plate/` holds an **independent left/right DXF pair** for all eight physical
layout permutations plus an independent universal pair. There is no rigid centre bridge: each plate half
follows its PCB and its own 3°-from-horizontal tent plane. Mutually exclusive switch positions
overlap, so a fixed-layout pair picks one layout while the universal pair merges
the overlapping openings into durable slots. Each plate follows its PCB
Edge.Cuts along the top, bottom, and stepped centre contours with a uniform
0.15 mm outward allowance for the larger plate apertures. Only the gasket sides
depart from the PCB shape: each half has one continuous straight outside gasket
wall and one continuous straight centre-facing gasket wall. Two integral
mounting tongues sit directly on each wall, giving two outer and two
centre-facing mounts per half. All use the same smooth-tapered 5 mm projection
geometry as the last complete plate revision. Every
switch/stabilizer opening remains inside the plate. The narrowest finished web
is 2.01 mm, preserving the project's conservative 2.0 mm POM target. The
daughterboard
mounts independently to the case and is not carried by either plate.

The production plate specification is **1.5 mm POM**. The Fusion plate bodies
use the same 1.5 mm thickness. Cutting tolerances and kerf compensation must be
applied by the plate fabricator rather than by rescaling the supplied DXFs.

Each PCB/plate half shares four aligned 2.2 mm isolated mounting holes. The two
halves intentionally use independently optimized patterns because mirroring
the points would collide with asymmetric FPC/multiplexer geometry. Use
non-magnetic nylon M2 spacers no larger than 4.0 mm OD. The complete spacer
bodies clear every switch and stabilizer opening in all eight fixed layouts and
the universal layout. The earlier flex-relief slots have been removed: the
plate material between switch, stabilizer and mounting openings is continuous.

The PCB halves retain their stepped, keymap-following outer contours. The plate
copies that profile, offset outward by 0.15 mm, before its gasket-bearing side
regions are replaced by four straight rails across the assembled keyboard. The
completed exterior uses a 1.0 mm material-side radius and remains an exact
left/right mirrored pair. Switch and stabilizer openings remain dimensionally
unchanged. The obsolete right-plate daughterboard carrier and its two holes
remain removed.

The fabrication names end in `-left.dxf` and `-right.dxf`; both files are needed
for one keyboard. Files without a side suffix are obsolete one-piece previews
and must not be sent for fabrication.

Each PCB/plate permutation has a correspondingly named
`plate/Symm60HE-gasket-pads-<layout>.dxf` with eight Poron pads matched to its
integral gasket tongues. `plate/Symm60HE-gasket-pads.dxf` is the universal
alias. No gasket feature or clamp is added to either Hall PCB, so gasket
compression remains isolated to the plate. Cut an upper and lower set from
1.5 mm Poron.

## Fusion 360 case-design reference

The previous generated case solids were removed from the active project. Import
`case/fusion360/Symm60HE-reference-assembly.step` into Fusion 360 and build the
case around its fourteen separately named reference bodies:

- left PCB and left universal plate
- right PCB and right universal plate
- compact daughterboard PCB
- populated left, right, and daughterboard electronic-component bodies
- left/right banks of Gateron KS-20 Magnetic Jade dimensional switch models
- left/right GMK CYL/Cherry-profile keycap banks for the primary 60-key
  `doe-wkl` layout, with the correct R1/R2/R3/R4 sculpt and key widths

The two plate/PCB pairs are each positioned 3° from horizontal (6° included
angle) with a 7° rear-up front-to-back
typing angle, with each PCB 5 mm below its plate. No case solid is included by
design. The Gateron switch exterior is reconstructed from the manufacturer's
KS-20TF10B045NW-Y89 drawing because Gateron does not publish a production STEP.
The cap bodies use licensed dimensional Cherry-profile CAD and match GMK's
published CYL profile, 1.5 mm double-shot ABS construction and MX-cross mount;
they are not GMK proprietary mold surfaces. Both banks can be hidden
independently. Individual STEP files make it easy to import each reference as
its own Fusion component; `Symm60HE-reference-assembly.FCStd` is the editable
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
| Segments | 1611 | 2411 | 716 |
| Vias | 247 | 418 | 74 |
| Signal copper | F.Cu + B.Cu | F.Cu + B.Cu | F.Cu + B.Cu |
| F.Cu pour | GND | GND | GND |
| B.Cu pour | GND | GND | GND |

### Explicit analog rail and dual GND pours

The current manufacturing design uses routed +3V3A rather than treating an
entire copper side as the analog supply. This leaves both sides available for
GND pours around the two-layer signal routing and makes the power path explicit
in the board connectivity. Stitching vias join the two ground layers and
isolated regions, and both GND pours use the board's 0.15 mm clearance and
thermal gap with a 0.18 mm minimum fill width, so copper survives between the
dense switch-field tracks without leaving necks below the connection-width
rule. A handful of GND pads that the south-pocket LED move
boxed in on both layers are tied to the plane by a tented 0.6/0.3 mm via inside
the pad (listed in the order checklist). KiCad refills the pours during DRC and
release generation.

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
- **The board is a compact 50 × 31 mm.** It includes four symmetric perimeter
  M2 NPTH mounting holes so the case can support it without a fastener through
  the populated centre or a hard mount to either keyboard half.
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
./build.sh          # rebuild current FFC production artifacts and all checks
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
maps all 69 physical channels through AML1-AML5 and AMR1-AMR5 and provides four
physical-layout profiles: WKL/split Backspace (60 active), Arrows/split
Backspace (63), WKL/2U Backspace (59), and Arrows/2U Backspace (62). Inactive
channels are excluded from both startup calibration and scan processing. A
profile change clears the old matrix state and recalibrates the newly selected
sensor set. Rapid trigger, adjustable actuation, SOCD/advanced keys,
calibration, and web-configurator support remain available.

The checked release binary is `firmware/build/firmware.bin`. To rebuild, install
the root requirements, run `python setup.py -k symm60he` in `firmware/libhmk`,
then `pio run -e symm60he`. A path without spaces is currently required by the
upstream link-map build step. Put the board in DFU mode with BOOT held while
resetting, install `dfu-util`, and run `pio run -e symm60he -t upload`.

## Manufacturing release

`release/jlcpcb/` contains two manufacturing orders:

- `Symm60HE-Half-Panel-Gerbers.zip`: both keyboard halves in one connected
  162.29 × 227.83 mm stacked panel, with thirteen five-hole mouse-bite rows at
  0.75 mm pitch, three B.Cu global fiducials, four 2 mm tooling holes, and all
  SMT parts on B.Cu
- `Symm60HE-Daughterboard-Gerbers.zip`: the separate compact, mixed-side
  daughterboard order, with only the four symmetric M2 NPTH case mounts and no
  additional local fiducial footprints

Both are 2-layer, 1.2 mm designs. The generated BOMs contain only fitted SMT
parts and every line has an exact LCSC assignment; isolated mounting holes and
other board-only features are omitted. The universal half-panel uses one
matched BOM/CPL pair that populates every Hall sensor and LED position. The
firmware profile masks positions unused by the selected physical layout.
Inspect both ZIPs in JLC's Gerber viewer before payment.

## What has been checked, and what has not

Checked against the current files:

- net audit clean: all 33 left and 36 right Hall channels reach an independent
  mux input and sensor; the address lines reach all five muxes and the ribbon;
  all ten ADC nets reach the MCU and their corresponding ribbon
- every board declares only `F.Cu` and `B.Cu`; +3V3A is routed and GND is
  poured on both sides
- all plate and gasket DXFs parse with zero `ezdxf` audit errors
- the Fusion reference assembly contains fourteen finite, separately named
  bodies, including populated electronics aligned to all three PCB solids
- all three native schematics pass KiCad ERC with zero messages, and their 786
  connected reference/pad/net assignments match the PCBs exactly
- the Symm60HE libhmk firmware compiles successfully for AT32F405RCT7; the
  current binary is 34,176 bytes and the linked image reports 14,072 bytes of
  RAM
- both fabrication ZIPs pass archive integrity checks and include both
  copper layers, masks, clipped silkscreens, Edge.Cuts, PTH and NPTH drills
- every normally ignored DRC rule was re-enabled in temporary projects; see
  `release/reports/ignored-drc-audit.md` and its raw reports

Still required before committing to a production quantity:

- inspect the four explicit 1.75 mm routed NPTH alignment slots in the
  universal half-panel with the selected fabricator's Gerber viewer; the fixed
  layout boards restore ordinary separated round alignment holes
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
