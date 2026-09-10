# Symm60HE

Symmetrical Hall effect Alice keyboard based off of the Doe — split into three
boards linked by ribbon cable.

GPLv3. Derived from FN40HE; see `NOTICE.md` for what is taken and from where.
The layout is a reconstruction of the DOE 60% by hare works, measured from
published photographs — not affiliated with that project.

The DOE 60% filled-WKL layout, built the way FN40HE is built (MT9102ET Hall
sensors, 8:1 analog muxes into an AT32F405RCT7) but cut into three boards linked
by ribbon cable:

| Board | Size | Carries |
|---|---|---|
| `pcb/Symm60HE-Left.kicad_pcb` | 157.9 × 105.9 mm | 33 switch positions, 4 muxes, 1 ribbon link |
| `pcb/Symm60HE-Right.kicad_pcb` | 155.5 × 106.4 mm | 36 switch positions, 4 muxes, 1 ribbon link |
| `pcb/Symm60HE-Daughterboard.kicad_pcb` | 62 × 32 mm | MCU, USB-C, ESD, both LDOs, crystal, BOOT/RESET, 2 ribbon links |

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

## Layout options on one PCB

The boards carry **69 switch positions** so a single pair of PCBs covers all
four layouts from the published layout page. Mutually exclusive positions share
a mux channel, the way the FN40HE BOM shares parts across its DNP columns:

- number row outer 2u — `=` + `]`, or one 2u backspace
- row 4 outer 2.25u — one shift, or ↑ + 1.25u shift
- bottom row outer 3u, each half — two 1.5u, or three 1u (`←↓→` on the right)

Left needs 31 channels, right 32; four muxes give 32 each.

## Plate

`plate/` holds one DXF per layout plus a universal one. They are separate files
because mutually exclusive switch positions overlap — a plate has to either pick
a layout or merge the overlapping openings into a slot, which is what the
universal plate does. Every plate clears a 4.90 mm minimum bridge between
openings and 10.79 mm from the plate edge to the nearest cutout.

## Case

`case/Symm60HE-case.scad` is parametric and matches the DOE's published spec:

| | |
|---|---|
| Typing angle | **11°** — the DOE's stated figure |
| Front height | 18.0 mm — the DOE quotes 14.7–20.1 mm excluding feet |
| Back height | 42.1 mm over 124.2 mm of depth |
| Mounting | isolated top, gasket ledge |
| Lateral tent | 0°, exposed as `lateral_tent_deg` |

**The DOE is not laterally tented.** Its spec sheet gives a typing angle and
nothing else, so "the same tenting the DOE has" is the 11° front-to-back angle.
`lateral_tent_deg` is left in as a parameter because a tented build was asked
for and the geometry supports it — raise it and the case will need feet on one
side to sit flat.

The bottom is flat and the top face is inclined: a wedge, which is what a tray
case actually is. Tipping the whole box instead would stand it on its front
edge. The pocket floor runs parallel to the plate, the way such a case is
milled — a flat pocket floor would leave the rear standoffs as 30 mm pillars.
That leaves 4.4 mm of material under the pocket at the front and 28.5 mm at the
back, and the daughterboard pocket is cut into that back solid, opening upward
into the main cavity for the ribbons and outward through the back wall for USB.

`docs/Symm60HE-case-section.svg` is a side elevation through the centre line.

## Routing

Two copper layers, and a design rule picked so that the router's own grid
enforces it: **0.2 mm traces, 0.15 mm clearance, 0.45/0.25 mm vias**. That is a
relaxed spec for any fabricator — 0.127/0.127 is the usual floor — and it is
what lets nets on cells 0.5 mm apart sit beside each other without a separate
spacing pass. Grid cells are 0.5 mm apart orthogonally and 0.354 mm diagonally,
and 0.2 + 0.15 = 0.35 mm fits inside the smaller of those.

Every component on the halves sits on the back, so the front copper is free to
be the **+3V3A plane**; the back carries the signals with a **GND pour** filling
round them. The daughterboard is populated on the front, so it pours GND on both
sides and stitches them together. Neither GND nor the analog rail is routed as a
net on the halves — see below.

| | Left | Right | Daughterboard |
|---|---|---|---|
| Connections routed | **74** of 82 | **76** of 88 | **27** of 36 |
| Segments | 646 | 747 | 178 |
| Vias | 127 | 146 | 28 |
| … of those, plane taps | 66 | 71 | 6 |
| Signals on | B.Cu | B.Cu | F.Cu |
| F.Cu pour | +3V3A | +3V3A | GND |
| B.Cu pour | GND | GND | GND |

### Why the analog rail is a pour, not a net

The rail reaches 75 pads on the left half. Routed as traces it is a spanning
tree across the whole board, and it gets there first and walls off the three
mux select lines, which have one shape that works and no slack. Routing the bus
first instead just moves the failure onto the rail.

So the rail stops being a net. **F.Cu is a +3V3A pour** — the halves carry no
components on the front, so it is very nearly solid — and every rail pad is tied
down to it by a via of its own, dropped just past the pad on its escape axis and
joined by a stub. FN40HE does the same thing with a `+3.3VA` zone of its own
alongside GND; it just puts it on the back, because its board is populated the
other way up. **B.Cu is the GND pour**, filling around the signals, and every
sensor and mux ground pin sits straight on it, so GND is never routed either.

That is not free: 66 vias through the sensor field block both layers, and they
cost almost exactly as much room as the traces they replaced. What it buys is a
real supply plane instead of a tree of 0.2 mm traces feeding 33 sensors, and it
is the arrangement the reference design uses.

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
- **The board grew from 56 × 26 mm to 62 × 32 mm.** The case pocket is derived
  from this outline, so the pocket grew with it; the back solid has the depth.
- **The USB-C receptacle moved off the centre line**, 10.5 mm right, to sit
  beside the MCU's USB pins rather than diagonally across the board from them.
  The case cutout follows the same offset — both come from `USB_X_OFF` in
  `tools/outline.py`.

What is left unrouted there is mostly the ribbon connectors' inner pins, where
twelve nets at 1.0 mm pitch have to escape inwards under the connector body.

## Building and checking

```sh
./build.sh          # regenerate everything from the KLE geometry
tools/verify.py     # just the checks
```

`verify.py` exits non-zero on any failure, so it works in CI.

## What has been checked, and what has not

Checked here, by script, against the generated files:

- all three boards parse as KiCad 10 s-expressions
- every board outline is a closed loop
- no footprint falls outside its board outline
- **zero pad-level conflicts** on all three boards, ignoring the pairs that are
  mutually exclusive by design
- net audit clean: every channel reaches exactly one mux input, one sensor and
  its decoupling; the address lines reach all four muxes and the ribbon; each
  ADC net reaches the MCU and one ribbon
- routing clean, against the real geometry rather than the router's own grid:
  every segment and via on-board and out of the USB-C keep-out, nothing within
  0.15 mm of a **pad, drill, trace or via belonging to another net**, no loose
  trace ends, both pours inside the outline. The trace-to-trace half of that is
  what catches two diagonal runs crossing through the same gap, which is a short
  no amount of cell bookkeeping will notice
- the mux and sensor nets on the halves follow FN40HE's architecture rather than
  memory: 8:1 muxes into 8 ADC inputs, inhibit tied locally

**Not** checked, because this environment has no KiCad, no OpenSCAD and no CAD
kernel:

- KiCad DRC and ERC have not been run
- there are no schematics yet — the boards carry their nets directly, which is
  valid and gives you a full ratsnest, but you will want to capture schematics
  before a production run. Symbol libraries are not vendored here for that
  reason; use KiCad's stock ones when you capture
- the pours are defined but not filled — KiCad fills them on open (press B)
- routing is partial — 74 of 82 on the left, 76 of 88 on the right, 27 of 36 on
  the daughterboard. Nothing unclean was written, but the remainder is yours
- the USB-C receptacle is the one footprint not generated. Its keep-out is now a
  real rectangle on `Dwgs.User` in the daughterboard file, which both the pad
  check and the router honour, and the BOM names the stock KiCad footprint to
  drop in
- the mux is SOIC-16 rather than FN40HE's TSSOP-16 — same chip, different
  package, for the reason given in `NOTICE.md`
- the case has not been rendered or printed; the SCAD is balanced and its
  modules resolve, but only OpenSCAD can confirm the booleans

## Files

- `Symm60HE-switch-map.csv` — every switch position, mm, rotation, which layouts use it
- `Symm60HE-channel-map.csv` — sensor → mux → channel, per half
- `Symm60HE-ribbon-pinout.csv` — the 12-way link
- `Symm60HE-BOM.csv` — both halves and the daughterboard
- `docs/Symm60HE-preview.svg` — plan view of the whole assembly
- `docs/Symm60HE-case-section.svg` — side elevation showing the 11° wedge
- `docs/img/` — rendered images of every board, the plate and the case
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
| Left | 163.5 × 115.8 mm, 183.7 cm² | **157.9 × 105.9 mm, 156.2 cm²** | 15% less |
| Right | 161.1 × 115.8 mm, 181.0 cm² | **155.5 × 106.4 mm, 155.5 cm²** | 14% less |

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
