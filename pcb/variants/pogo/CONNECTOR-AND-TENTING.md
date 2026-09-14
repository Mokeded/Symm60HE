# 12-contact pogo connector and tenting definition

This is the connector, stack, retention and release-gate definition for the
routed `../pogo-neo/` boards. It supersedes the 16-contact 2 × 8 definition
that this file previously described; that stream is summarised at the end
because its coupons remain useful first articles.

## Selected connector pair

- Spring side: Mill-Max `854-22-012-30-004101`, 12 contacts in a single row
  on 1.27 mm pitch, SMT, gold-plated. Reference `PS1` on each spring module.
- Target side: Mill-Max `856-10-012-30-051000`, matching 12-contact single-row
  SMT gold target. Reference `PTL1` / `PTR1`, soldered directly to each Hall
  PCB.
- Both parts are exact verified-supplier STEP models under
  `case/fusion360/models/vendor/`, hash-locked in
  `case/fusion360/models/model-provenance.json`. They are dimensioned from
  those models, not from a generic package.
- Neither part is in the JLCPCB/LCSC library. Every generated BOM leaves the
  LCSC field blank on purpose; source them by consignment, PCBWay turnkey
  quotation, or hand installation as described in
  `release/jlcpcb-pogo-neo/README.md` and
  `release/pcbway-pogo-neo/PCBWay-RFQ-Notes.txt`. No substitute is authorised.
- The interface is power-off-only. It has no staggered contacts, pre-charge,
  connector-present input or load switch, so mating while USB is connected is
  outside the design envelope.

## Electrical definition

The 12 contacts carry exactly the 12 conductors of the existing ribbon link:
four ADC channels, three MUX select lines, +3V3A and four grounds. The
per-half order is fixed in `../pogo-neo/Symm60HE-neo-pogo12-pinout.csv`;
grounds are interleaved with the ADC contacts and the right half uses the
reversed contact order of the left, so each half has its own spring-module
board (`Symm60HE-Neo-Left-SpringModule`, `-Right-SpringModule`). The MUX select pins are
low-speed digital signals. There is no hot-plug-detect contact because hot
plugging is not a requirement.

## Mechanical architecture

The topology follows the Qwertykeys Neo Ergo daughterboard: a flat central
controller, two identical replaceable pogo modules on flex pigtails, and main
PCBs that drop directly onto the modules.

| Element | Definition |
|---|---|
| Controller | 57 × 27 mm, flat, lengthwise under the centre blocker; one continuous straight rear edge with the HRO USB-C shell projecting 1.0 mm beyond it. Rigidly held on a 1.2 mm floor by two M2 fasteners in its existing NPTH holes plus two compliant edge ledges. |
| Spring module | 20 × 6 × 1.2 mm PCB: the 854 spring row on F.Cu, the BOOMELE `1.0-12P` (LCSC `C20111`) ZIF connector directly behind it on B.Cu. No holes through the fanout. |
| Module retention | Captured in a kernel aperture tilted to its half's 3° tent plane, 0.4 mm X/Y clearance per side, asymmetric perimeter keys for X/Y/θ registration, capture lips that prevent fall-out without clamping, four 0.8 mm Poron 4701-30 pads underneath. The module floats so it can follow gasket motion. |
| Target | 856 soldered to the Hall PCB in place of the FFC connector. There is no target daughterboard and no second flex. |
| Interconnect | One custom 12-conductor same-side FPC jumper per side, 0.3 mm reinforced tails, into the controller's ZIF. Finished length and service loop come from the completed case CAD; continuity-check pins 1–12 before first power. |
| Hard stops | Four per side, defining the board-to-board spacing below. They, not the magnets, set the stack. |
| Suspension | Plate-only: eight side gasket pads (four outer, four centre-side). No top/bottom tabs and no gasket features on any PCB, so typing and case preload never enter the sensor board or the connector. |

## Mating stack

Derived from the exact vendor models (`case/fusion360/models/vendor/README.md`):

- Free stack, target face to spring housing face, is 5.2578 mm.
- The reference assembly sets **5.0 mm** mating-surface spacing, which applies
  0.2578 mm preload and leaves 0.7582 mm of the published 1.016 mm stroke.
- The earlier 6.0 mm placeholder spacing would leave a 0.7422 mm open gap with
  the exact models. `case/fusion360/tenting-solution/dimensions.json` and
  `case/fusion360/pogo-neo-mounting-reference/dimensions.json` still carry
  that placeholder stack and the older 20 × 20 mm module size; treat the main
  `Symm60HE-case-reference-assembly.step` as authoritative until those
  auxiliary references are regenerated.
- The spring-travel keep-out bodies reserve the full initial-height envelope;
  do not build case features inside them.
- Mill-Max's published mid-stroke contact force must be confirmed on the
  current drawing; with the previously quoted 50 g per contact, twelve
  contacts oppose closure with roughly 600 gf (5.9 N) per interface before
  tolerance and shock margin. Retention must be positive (lips, stops, case
  preload), not magnetic.

## Magnets

Magnets remain **DNP until an assembled Hall test passes**. Any pocket in the
case references is a retention experiment only and may be replaced by
non-magnetic hardware or a snap latch. No release may populate magnets until a
complete assembled keyboard shows acceptable zero-field offset, idle noise,
full-travel calibration and Rapid Trigger chatter margin for every switch.
CAD distance alone is not evidence that a magnet is safe near a Hall sensor.
This is the one deliberate departure from the Neo Ergo, which carries a magnet
at each end of every module and has no Hall sensors to disturb.

## Relationship to the Neo Ergo daughterboard

| Neo Ergo | Symm60HE `pogo-neo` |
|---|---|
| Flat daughterboard in an aluminium kernel tray | Flat controller under the centre blocker |
| Two identical replaceable pogo modules, separate from the daughterboard | Two 20 × 6 mm floating spring modules |
| Module FPC pigtail into a ZIF on the daughterboard | 12P FPC jumper into the C20111 ZIF on the controller |
| Modules located by a kernel pocket | Captured 3° apertures with keys and lips |
| Main PCB drops onto the modules, no cable | Hall PCB mates directly through the 856 target |
| Custom 2 × 7 OEM module, magnets at both ends | Catalogue 1 × 12 Mill-Max pair, magnets DNP |
| PCB side is bare gold pads | PCB side is a soldered 856 target |

The last row is the remaining structural difference. Mill-Max 854 plungers
are rated to mate against flat gold pads, so a bare hard-gold pad field on the
Hall PCB would remove two Mill-Max parts per keyboard, lower the stack and
match the Neo Ergo exactly, at the cost of the 856's harder wear surface.
That option is not in the routed boards; evaluate it on a coupon before
changing them.

## Superseded 16-contact stream

The original alternate used Mill-Max `855-22-016-30-004101` /
`857-10-016-30-051000`, 16 contacts in a 2 × 8 array on 1.27 mm pitch, with
20 × 20 mm spring and target heads and a second FPC on the target side. Its
pinout is retained in `Symm60HE-pogo16-pinout.csv`, its coupons under
`coupon/`, and their Gerbers under `release/pogo16-prototype/`. The routed
`pogo-neo` boards replaced it because the 12 existing ribbon conductors need
no second row, the direct target removes a board and a flex per side, and the
narrow 20 × 6 mm modules no longer overlap at the target-row separation. The
16-contact coupons still exercise the same Mill-Max land pattern family and
mid-stroke stack, so they remain a valid first article for solder, tolerance
and cycle testing; they do not validate the 12-position geometry.

## Prototype and release gates

1. Confirm the two 12-position land patterns against the current Mill-Max
   product drawings and an actual received part before ordering assembled
   keyboard PCBs. Confirm the published contact force and initial height at
   the same time.
2. Fit one 854/856 pair to a coupon and continuity-test all 12 contacts while
   sweeping the allowed X/Y/Z and angular tolerance of the floating module.
3. Measure the hard-stop stack and confirm the 5.0 mm spacing at every corner;
   reject any stack that can bottom the 1.016 mm stroke or open the contacts.
4. Verify the FPC jumper path at both gasket travel limits with a service loop
   inside the supplier's dynamic bend radius, then fix its length in the BOM.
5. Repeat at least 100 mate cycles, then recheck contact resistance and all
   ADC noise channels.
6. Run assembled Hall zero-field, idle-noise, full-travel and Rapid Trigger
   chatter tests with magnets omitted; repeat with magnets only if that first
   test passes.
7. The routed `pogo-neo` boards may be promoted to a keyboard manufacturing
   release only after all of the preceding mechanical and electrical tests
   pass. Until then the flexible-interconnect keyboard under `release/jlcpcb`
   remains the checked production candidate.
