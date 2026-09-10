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
| `pcb/DOE60-Left.kicad_pcb` | 157.9 × 105.9 mm | 33 switch positions, 4 muxes, 1 ribbon link |
| `pcb/DOE60-Right.kicad_pcb` | 155.5 × 106.4 mm | 36 switch positions, 4 muxes, 1 ribbon link |
| `pcb/DOE60-Daughterboard.kicad_pcb` | 56 × 26 mm | MCU, USB-C, ESD, both LDOs, crystal, BOOT/RESET, 2 ribbon links |

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

`case/DOE60-case.scad` is parametric and matches the DOE's published spec:

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

`docs/DOE60-case-section.svg` is a side elevation through the centre line.

## Routing

A first pass, all of it machine-checked:

| | Left | Right | Daughterboard |
|---|---|---|---|
| Segments | 68 | 72 | 0 |
| Vias | 33 | 33 | 0 |
| Pours | +3V3A on F.Cu, GND on B.Cu | same | same |

Two planes. Every component sits on the back, so the front copper is empty and
becomes the **+3V3A plane**; the back carries the **GND pour**, which fills
around the signal traces. Both use `connect_pads`, so every GND pad ties in
without a single trace and each analog-rail pad needs only a via.

Chaining the rail sensor-to-sensor was the obvious first attempt and it was
wrong — a straight line between two sensors' VCC pads runs straight through the
MX leg holes between them. The checker found 24 clearance violations; the plane
approach removed them.

The router routes around obstacles rather than assuming a clear line: straight
if it fits, otherwise an L in either order, and if neither is clear it leaves
the connection for you and says so. Five connections across both halves came
back that way. Drilled holes count as obstacles **even when they belong to a
switch position your layout does not populate** — the hole is there either way,
which is a trap specific to a multi-layout board.

**Sensor signal to mux input is deliberately not routed.** That is the part
worth doing with a real router, and it is the bulk of the remaining work.

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
- routing clean: every segment and via on-board, no trace or via within 0.20 mm
  of a pad or drill on another net, no loose trace ends, both pours inside the
  outline
- MCU pin assignment lifted from the FN40HE board rather than from memory

**Not** checked, because this environment has no KiCad, no OpenSCAD and no CAD
kernel:

- KiCad DRC and ERC have not been run
- there are no schematics yet — the boards carry their nets directly, which is
  valid and gives you a full ratsnest, but you will want to capture schematics
  before a production run. Symbol libraries are not vendored here for that
  reason; use KiCad's stock ones when you capture
- the pours are defined but not filled — KiCad fills them on open (press B)
- most signal routing is still to do, as above
- the USB-C receptacle is the one footprint not generated; its position and
  keep-out are marked on the daughterboard and the BOM names the stock KiCad
  footprint to drop in
- the case has not been rendered or printed; the SCAD is balanced and its
  modules resolve, but only OpenSCAD can confirm the booleans

## Files

- `DOE60-switch-map.csv` — every switch position, mm, rotation, which layouts use it
- `DOE60-channel-map.csv` — sensor → mux → channel, per half
- `DOE60-ribbon-pinout.csv` — the 12-way link
- `DOE60-BOM.csv` — both halves and the daughterboard
- `docs/DOE60-preview.svg` — plan view of the whole assembly
- `docs/DOE60-case-section.svg` — side elevation showing the 11° wedge
- `docs/img/` — rendered images of every board, the plate and the case
- `tools/` — generators and checkers; `build.sh` runs them in order
- `DOE60_Project.pretty/` — the footprint library, local and portable

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
