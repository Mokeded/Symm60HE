# 16-contact connector and tenting definition

## Selected connector pair

- Spring side: Mill-Max `855-22-016-30-004101`, 16 contacts in a 2 × 8
  array on 1.27 mm pitch, SMT, gold-plated, 4.2 mm free height.
- Target side: Mill-Max `857-10-016-30-051000`, matching 16-contact 2 × 8
  SMT gold target connector.
- Nominal board-to-board spacing is 6.0 mm at 0.5 mm mid-stroke. The case
  hard stops, not the magnets, establish this dimension.
- Mill-Max specifies 50 grams of force per contact at mid-stroke. Sixteen
  contacts therefore oppose closure with about 800 gram-force (7.85 N) per
  interface before tolerance and shock margin. Use nonmagnetic M2 screws or a
  positive snap latch for the first prototype. The magnet pockets are an
  optional experiment, not the primary retention recommendation.
- The interface is power-off-only. It has no staggered contacts, pre-charge,
  connector-present input, or load switch, so mating while USB is connected is
  outside the design envelope.

The pinout is in `Symm60HE-pogo16-pinout.csv`. Two +3V3A contacts and seven
ground contacts reduce contact resistance and place returns beside the four
ADC channels. The MUX select pins are low-speed digital signals. There is no
hot-plug-detect contact because hot plugging is not a requirement.

## Tented mechanical architecture

A single flat controller PCB cannot mate normally to two keyboard PCBs on
opposite 3 degree tent planes. The rebuilt `pogo-neo` architecture therefore
uses two independently angled 20 x 20 mm replaceable spring heads. Each is parallel to
its keyboard half and retained by the central controller cradle. A short,
strain-relieved 12-way FPC connects each spring module to the flat controller.
A matching 20 x 20 mm target head travels with the Hall-PCB assembly and
connects through another short 12-way FPC. This follows the Neo-style mating
topology while keeping the target interface replaceable.

Each interface has:

- a captured, asymmetric perimeter-keyed carrier pocket for X/Y/theta
  registration without adding holes to either connector module;
- four hard stops defining 6.0 mm board-to-board spacing at 0.5 mm spring
  compression;
- 0.8 mm Poron support pads behind the modules so the electrical connector does
  not carry typing or case-assembly loads;
- two provisional 4 × 2 mm N35 axial disc-magnet pockets with mild-steel
  backing washers.

Keyboard suspension is separate from the connector carrier. Six gasket pads
are integral to the split plates only: two on each outside edge and one on
each centre-facing edge. There are no top/bottom gasket tabs and no gasket
features on the Hall PCBs, so typing and case preload are transferred through
the plate rather than through the sensor board.

The magnets are marked `DNP UNTIL HALL TEST`. Their pockets are retention
features only and may be replaced by nonmagnetic M2 screws or snap latches.
No release may populate magnets until a complete assembled keyboard shows
acceptable zero-field offset, idle noise, full-travel calibration and Rapid
Trigger chatter margin for every switch. CAD distance alone is not evidence
that a magnet is safe near a Hall sensor.

## Prototype and release gates

1. Confirm the two footprint land patterns against the current Mill-Max
   product drawings and an actual received part before ordering assembled
   keyboard PCBs.
2. Fabricate the spring and target coupons in `release/pogo16-prototype`, fit
   one connector pair, and continuity-test all 16 contacts while sweeping the
   allowed X/Y/Z and angular tolerance.
3. Measure the hard-stop stack and confirm 0.5 mm compression at every corner;
   reject any stack that can bottom the 1.0 mm stroke.
4. Repeat at least 100 mate cycles, then recheck contact resistance and all ADC
   noise channels.
5. Run assembled Hall zero-field, idle-noise, full-travel, and Rapid Trigger
   chatter tests with magnets omitted; repeat with magnets only if that first
   test passes.
6. The routed `pogo-neo` boards may be promoted to a keyboard manufacturing
   release only after all of the preceding mechanical and electrical tests
   pass.
