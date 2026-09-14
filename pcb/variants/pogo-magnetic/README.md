# Magnetic-pogo variant

Same architecture as `../pogo-neo/` — rigid controller, one floating module per
side, target soldered straight to the Hall PCB, one 12-way FPC jumper per side
— with the Mill-Max 854/856 pair replaced by a **12-contact magnetic pogo pair
in two rows of six**. The magnets are in the connector housing and pull the
joint into alignment. That is the entire point: the 854/856 pair butts flat and
self-aligns only within 0.0596 mm radial (see
[`../pogo/MATE-AND-ASSEMBLY.md`](../pogo/MATE-AND-ASSEMBLY.md)), while the
kernel aperture lets the module float 0.4 mm per side.

**This is a prototype stream, not a release.** `../pogo-neo/` remains the
routed and released architecture. Read "Status" before ordering anything.

## The connector

No catalogue manufacturer publishes a datasheet for a 12-contact magnetic pogo
pair in a keyboard-sized envelope. Mill-Max's own magnetic line, Maxnetic
878/879, stops at six positions on a 4 mm pitch and stands 9.6 mm above the
board. LCSC stocks single probes, not multi-contact magnetic pairs. What does
exist is an ODM family — CFECONN, SUNMON, Promax, Johoty, KLS all build it —
and the same family in stocked form on AliExpress as "dual row magnetic pogo
pin connector, 8/10/12/14/20 pole, 2.54 mm". Qwertykeys' own Neo Ergo part is
from the 2.0 mm branch of that family: measured off their build guide it is
2 × 8 on ~2.0 mm with ~2.8 mm between rows and a magnet at each end.

So these boards are cut to an interface control drawing rather than to a
supplier part number, and the footprints carry the ICD name, not an MPN.

### Parts surveyed

Recorded so nobody repeats the search. Every catalogue reachable splits the
two properties this design needs -- *rectangular multi-contact* and *magnetic*
-- across separate product lines.

| Part number | What it is | Why it is not the part |
|---|---|---|
| Mill-Max `878`/`879` Maxnetic | magnetic, full datasheet, 1,000,000 cycles, 25 mOhm, 7.2 A | 2-6 positions only, 4 mm pitch, 9.6 mm above board |
| CFECONN `MP819-1133-G16100A` | 2.0 mm, 16 pin, double row, 1.40 mm stroke, 70+/-20 gf, 1 A, 50 mOhm, 100k cycles | no magnets, and DIP rather than SMT |
| CFECONN `BF302501-12200L0F` | 12-pin signal pogo connector | no magnets |
| CFECONN `MFA038801` | magnetic pogo connector | round, low pin count |
| KLS `KLS1-12PGC01B` | double row 12 pin pogo connector | no magnets; MOQ 1000; dimensions only on request |
| SUNMON `906-00016` | 12 contact **female**, single row, 2.54 mm, IP65, 16 V/2 A, 30 mOhm, -40/+105 C, 3u" Au | no magnets in the drawing's bill of materials, screw-mounted, and 46.27 mm long overall |
| SUNMON `905-00030` | 12 contact **male**, 2 x 6 on 2.54 x 2.54 mm, 12.70 mm field, 2 A, 50 mOhm, 40+/-15 gf at 1.0 mm stroke, 1.20 mm full stroke, 20,000 cycles | no magnets, but the right land pattern -- see below |
| SUNMON `905-00176` | 14 contact **male**, 2 x 7 on 3.60 x 3.60 mm, 21.60 mm field, 1 A, 50 mOhm, 50+/-10 gf, 1.70 mm full stroke, 10,000 cycles; catalogued as "Magnetic Type" | 3.60 mm pitch is too coarse, and the magnets are not in it -- see below |
| AliExpress "dual row magnetic pogo, 8/10/12/14/20 pole, 2.54 mm" | magnetic, double row, 12 pole, stocked | no part number, no datasheet, no model, seller can change it silently |

CFE's magnetic range is round, 2-8 pin; their rectangular multi-pin range is
not magnetic. Mill-Max's magnetic range stops at six positions. That is the
whole market as far as published data goes.

The last row is the one to buy for a first prototype: it is the right
geometry family and it ships tomorrow. Measure what arrives before trusting
any dimension in the ICD below.

### Twelve contacts and up: what is actually stocked

Contact span is what decides whether a part fits the kernel, so it is the
column that matters. (An earlier revision of this file said no manufacturer
catalogue published a magnetic part above eight contacts. That was wrong --
see "Catalogue magnetic parts with nine contacts and up" below.)

| Family | Positions offered | Contact span at 12 | at 14 | at 16 |
|---|---|---|---|---|
| Single row, 2.54 mm, 2 A, screw holes | 13-20 | 27.94 | 33.02 | 38.10 |
| Single row, 2.54 mm, 10 A/36 V, "with ears" | 12-20 | 27.94 | 33.02 | 38.10 |
| Single row, 2.54 mm, ribbon cable attached | 7-20 | 27.94 | 33.02 | 38.10 |
| Single row, 2.8 mm | 2-14 | 30.80 | 36.40 | -- |
| **Dual row, 2.54 mm** | 8, 10, 12, 14, 16, 20 | **12.70** | **15.24** | **17.78** |
| Dual row, 2.0 mm | 4, 6, 8, 10 | -- | -- | -- |
| Neo Ergo's own part (measured, not sold) | 2 x 8 on ~2.0 mm | -- | -- | 14.00 |

Add roughly 12 mm to a contact span for the magnets at each end to get the
housing. A single-row 12-contact part is therefore a ~40 mm housing needing a
~47 mm module; the 2 x 6 dual row is a 25 mm housing on the 32 mm module this
variant builds. That is why the dual row wins here even though the single row
is the easier fanout and maps one-for-one onto the Mill-Max routing.

Sixteen contacts is available in the dual-row family and is a one-line change
here (`PER_ROW = 8`, then re-run both generators). It was tried: it generates
and routes, costs 5 mm of module length, and leaves three clearance flags on
the left half instead of two -- so that crossing is the anchor geometry, not a
shortage of slots. What the four spare contacts buy is worth having anyway:
doubled grounds and a paralleled `+3V3A`, which matters more than usual across
a 50 mOhm contact carrying an analog rail. Twelve is what is committed here
because it is the smaller module; sixteen is the better electrical choice if
the case can spare the width.

### Where to buy

Verified live at the time of writing:

- [Dual row, 2.54 mm, 8/10/12/14/20 pole](https://www.aliexpress.com/item/3256804721860036.html)

Found through search metadata but not fetched directly, so confirm the listing
before ordering:

- [Dual row, 2.54 mm, 8/10/12/14/16/20 pin](https://www.aliexpress.com/item/3256808221496755.html)
- [Dual row, 2.54 mm, 8/10/12/14/16/20 positions](https://www.aliexpress.com/item/3256808648135588.html)
- [Single row, 2.54 mm, 12-20 pin, 10 A, with ears](https://www.aliexpress.com/item/3256812836315769.html)
- [Single row, 2.54 mm, 13-20 pin, 2 A](https://www.aliexpress.com/item/3256812629914566.html)

None of these carries a part number or a datasheet. Buy one pair, measure it,
and only then trust the ICD.

### SUNMON 906-00016, and why the land pattern below is no longer invented

`906-00016` is a real SUNMON part with a published drawing
(`smeconn.com/wp-content/uploads/2026/04/906-00016.pdf`), but it is not the
part for this design and it is not magnetic. The drawing shows a **single row**
of twelve contacts on 2.54 mm, 27.94 mm of contact field inside a 46.27 mm
body with screw ears on 39.48 mm centres, and a bill of materials with exactly
two lines: twelve gold-plated pins and one black HTN housing. No magnet. The
catalogue blurb calling it a "magnetic waterproof design" is not borne out by
the drawing.

Its male counterpart is not published. SUNMON's drawings carry legacy numbers
in a readable scheme -- `PPF.` for the female half, `PPM.` for the male -- and
`906-00016` is `PPF.12-1257-0302 / TC528-12D254-A`. The nearest published male,
`905-00217` "12Pin IP65 Waterproof", is `PPM.12-505-0502 / PC719-12S300-A`:
twelve contacts, but on **3.00 mm**, so it does not mate. SUNMON do publish
pairs when they have them (`906-00005 / 905-00011`, `904-00020 with 903-00015`),
so the mate exists internally -- ask them for the `PPM` half of
`PPF.12-1257-0302`.

The useful find in that catalogue is **`905-00030`**, a 12-contact male in
**two rows of six on a 2.54 x 2.54 mm grid, 12.70 mm contact field** -- exactly
the geometry this variant is cut to, with a real drawing behind it. It is not
magnetic, but it confirms the contact block below is a shape the industry
actually builds, and it publishes a recommended layout:

| | ICD here | SUNMON `905-00030` |
|---|---|---|
| Array | 2 x 6 | 2 x 6 |
| Pitch / row gap | 2.54 / 2.54 | 2.54 / 2.54 |
| Contact field | 12.70 x 2.54 | 12.70 x 2.54 |
| Land diameter | **1.50** | **2.00** |
| Contact force | unknown | 40 +/- 15 gf at 1.0 mm working stroke |
| Full stroke | unknown | 1.20 mm |
| Current / resistance | unknown | 2 A / 50 mOhm max |
| Durability | unknown | 20,000 cycles |

### Catalogue magnetic parts with nine contacts and up

SUNMON publish magnetic connector families at **9, 10, 16, 18 and 42 pin**,
with drawings, part numbers and a mating half named for each. These are not
the magnet-compatible pogo blocks described in the next section: their bills of
materials list N52 NdFeB magnets with Ni-Cu-Ni plating as line items.

| Pair | Contacts | Layout | Body | Electrical | Mechanical |
|---|---|---|---|---|---|
| **`903-00081` / `904-00080`** (DIP PCB) | **9** | two staggered rows, 1.50 mm pitch, 6.00 mm field | **19.80 x 8.30 x 4.50 mm** | 12 V, 1 A, 50 mOhm max, 100% open/short tested | 30+/-10 gf at 0.50 mm working stroke, **0.70 mm full stroke**, 10,000 cycles, -30/+60 C |
| `903-00082` / `904-00079` | 9 | same, wire-solderable instead of DIP | — | as above | as above |
| `903-00018` / `904-00023` | **10** | `MC146-10R` | — | 12 V, **2 A**, 50 mOhm | 40+/-15 gf, 0.60 mm working stroke, **850 gf docking force**, 10,000 cycles, -25/+85 C |
| `903-00015` / `904-00020` | 8 | single row, 2.00 mm pitch, 14.00 mm field | 32.51 x 7.41 x 3.90 mm | 12 V, 1 A, 50 mOhm | 35+/-10 gf, 1.00 mm full stroke, IP65 |
| `903-00017` / `904-00022` | 9 | high current, waterproof | — | — | — |
| `903-00044` / `904-00058` | 9 | round | — | — | — |
| `903-00042` | 18 | male | — | — | — |

`903-00081` is the one that matters for a nine-conductor-per-half link: nine
contacts in a 19.80 x 8.30 mm body, polarity-keyed by an N and an S magnet at
the ends so it can only mate one way, and a genuine PCB mount. Legacy number
`MC142-09R-BM`.

Two things to weigh against it. Its **0.70 mm full stroke** is well under the
Mill-Max `854`'s 1.016 mm, so there is less compliance available to absorb
gasket motion -- check that against the travel the module actually sees. And at
1 A and 50 mOhm it is a signal connector; the `+3V3A` analog rail crossing one
of those contacts is the thing to measure on a coupon.

### The magnets are probably not in the connector

This applies to the `905`/`906` pogo blocks, not to the `903`/`904` magnetic
pairs above. Three `905`/`906` drawings have been read -- `906-00016`,
`905-00030` and `905-00176` -- and every one has a bill of materials with
exactly two lines: gold-plated pogo pins, and a black HTN UL94 V-0 housing.
**No magnet, on any of them**, including `905-00176`, which their catalogue
lists as "14PIN Male Connector (Magnetic Type)" and describes as "magnetic
attraction compatible".

That phrase is the tell. These are magnet-*compatible* pogo blocks: the
magnets are meant to sit in the customer's housing around the connector, not
inside the part. Qwertykeys' own Neo Ergo connector does carry its magnets
inside the moulding, but that is a custom part built on their volume; nothing
in a public catalogue works that way above a handful of contacts.

This reframes the sourcing problem, and it reopens an option dismissed earlier
in favour of chasing an integral-magnet part:

- a catalogue pogo pair carries the contacts -- `905-00030` for this land
  pattern, or the Mill-Max `854`/`856` pair already routed in `../pogo-neo/`,
  which is better on every electrical figure (20 mOhm against 50, 7 A against
  2, 0.51 um gold, exact vendor STEP);
- two catalogue magnets, a fully specified BOM line, sit in the module and the
  kernel and do the aligning.

That combination is orderable today, keeps the hash-locked vendor models, and
still closes the 0.0596 mm alignment gap that motivated this variant. It should
be costed against the ICD part before anyone pays for tooling.

### Land pattern

The land is the one disagreement. Setting `PAD = 2.00` in
`tools/make_mag_pogo_footprints.py` matches SUNMON's recommendation and was
measured: it keeps both modules clean but takes the two halves from two
clearance flags to nine, because the larger lands crowd the breakout. Left at
1.50 here so the committed boards stay at their best verified state; move it
to 2.00 and rework the halves once a real magnetic drawing fixes the number.

### ICD MAGPOGO-2x6-P254

| | |
|---|---|
| Contacts | 12, two rows of six |
| Pitch along a row | 2.54 mm |
| Row to row | 2.54 mm |
| Contact field | 12.70 x 2.54 mm |
| Land diameter | 1.50 mm, SMT |
| Magnets | one at each end of the contact block, centres 21.0 mm apart. See the note below: on catalogue parts these are the customer's, not the connector's |
| Solder anchors | 3.2 mm square under each magnet boss, mechanical only |
| Housing envelope | 25.0 x 9.0 mm max |
| Courtyard | 26.0 x 10.0 mm |
| Mating | spring half on the module, target half on the Hall PCB |
| Plating | gold over nickel on both halves |
| Policy | power-off only; no hot plug |

Order to this drawing from any of the houses above and ask for the mating
drawing back. **Every dimension here is a requirement I set, not a dimension
read off a supplier drawing.** Confirm the housing envelope, the land pattern
and the seated stack against the drawing that comes back, then regenerate:
the footprints are written by `tools/make_mag_pogo.py`'s constants, so a
changed dimension is a one-line edit and a re-run, not a re-layout.

The 2.0 mm branch is the alternative: it matches the Neo Ergo's own tooling,
which is the only magnetic pogo proven in this exact application, at the cost
of a tighter land pattern. Change `PITCH` and `ROW_GAP` and re-run.

## What changed on the boards

| | `pogo-neo` | here |
|---|---|---|
| Contacts | 1 x 12 on 1.27 mm | 2 x 6 on 2.54 mm |
| Spring module | 20 x 6 mm | 32 x 18 mm |
| Contact escape | straight to the ZIF | far row steps half a pitch out through the near row's gaps |
| Ground | paired to the ZIF | own F.Cu bus, kept out of the signal fan |
| Target on the Hall PCB | 1 x 12, one column | 2 x 6, two columns, near column on B.Cu and far column hopping to F.Cu |
| Alignment | case only, 0.0596 mm radial | magnets, plus the case |

The contact map is not hand-written. `solve_contact_map` picks it, because two
orderings have to hold at once and neither is ours to choose: the module's
escape lanes must run in the ZIF's net order, and each contact column on the
Hall PCB must reach its handoff anchors without crossing. See
`Symm60HE-mag-pogo12-pinout.csv` for the map it found.

## Status

Verified by `tools/verify_mag_pogo.py`, which checks copper inside the
outline, 0.15 mm clearance between nets per layer, dangling ends, and that
every contact carries a net:

| Board | Result |
|---|---|
| `Symm60HE-Mag-Left-SpringModule` | clean |
| `Symm60HE-Mag-Right-SpringModule` | clean |
| `Symm60HE-Mag-Right-Half` | clean |
| `Symm60HE-Mag-Left-Half` | **2 clearance flags** |

The two flags are one crossing: `MUX_A0` and `ADC_L1` have anchors 0.88 mm
apart and arrive from opposite contact columns, so they meet on F.Cu in the
last millimetre before the handoff. The solver prefers assignments that keep
anchor-adjacent nets in one column and manages it on the right half; on the
left the anchor order the inherited routing hands us does not allow it. Fix it
by hand in the layout editor, or by moving one of those two anchors, before
this half goes anywhere.

**No KiCad DRC has been run on these boards.** KiCad 10 was not available in
the environment that generated them, and `tools/verify_mag_pogo.py` does not
refill zones, so pour clearance is unchecked. Run `tools/verify_neo_pogo.py`'s
DRC step against these files before treating any of it as real.

Also still open: the module grew from 20 x 6 mm to 32 x 18 mm, so the kernel
aperture, capture lips, compression stops and the spring-travel keep-out in
`case/fusion360/` are all stale for this variant. The seated stack is unknown
until a supplier drawing arrives, so the 5.0 mm board-to-board figure does not
carry over either.

## Regenerate

```sh
./.venv/bin/python tools/make_mag_pogo.py
./.venv/bin/python tools/verify_mag_pogo.py
./.venv/bin/python tools/render_mag_pogo.py   # docs/img/42
```
