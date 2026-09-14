# Symm60HE fixed-tent pogo/controller module

This is the recommended first-prototype tenting mechanism for the 12-contact
pogo alternate. It is a fixed 3 degree design matching the keyboard reference
assembly; it does not try to use the pogo connector as a hinge.

## Architecture

- The 57 x 27 mm MCU daughterboard is held lengthwise in the central 61 x 32 mm
  printed tray.
- Separate 20 x 20 mm spring-head PCBs float in left and right kernel apertures tilted so
  both centre-facing edges are raised: -3 degrees on the left and +3 degrees
  on the right when viewed from the front. Each spring connector is therefore
  parallel to the direct target on its Hall PCB.
- Two printed ribs per side join the central tray to each fixed-angle connector pocket.
- The 12-contact targets are soldered directly to the **Hall-PCB assemblies**,
  matching the Neo Ergo topology. There are no target receiver frames or
  target PCBs. This is separate from keyboard suspension; all gasket support
  remains on the plates.
- Asymmetric perimeter keys in each captured pocket establish X/Y/theta and
  prevent 180 degree installation without drilling the module fanout.
- Four POM hard stops per side define 6.0 mm mating-surface-to-mating-surface
  PCB spacing and about
  0.5 mm nominal spring compression.
- Each spring head has 0.4 mm X/Y clearance per side. Capture lips prevent it
  from falling out but do not clamp it, allowing the head to follow gasket
  motion. Only the controller uses M2 edge clamps.
- One short 12-way FPC connects the rigid controller to each floating spring
  head. These are the only ribbon cables in the pogo implementation.
- Four 0.8 mm Poron 4701-30 pads support each wing PCB and accommodate small
  printed-part and PCB-thickness variation.

## Retention

Use nonmagnetic M2 screws or positive case snap latches for the first build.
At the connector's specified 60 grams per contact, 12 contacts generate about
7.06 N opening force at mid-stroke before shock margin. Do not rely on friction
or on the electrical contacts to hold the case together.

The model includes two optional 4 x 2 mm N35 axial magnet envelopes per side,
but they are tagged `DNP_Until_Hall_Test`. They are not the recommended first
build. If magnets are tested, add mild-steel backing cups and compare all Hall
channels with magnets absent/present through the complete switch travel.

## Suggested prototype BOM

| Item | Quantity | Specification |
|---|---:|---|
| Central tray/spine | 1 | PA12-CF SLS/MJF preferred; PETG acceptable for fit check |
| Angled spring-head carrier | 2 | Printed as separate left/right bodies |
| Spring head PCB | 2 | 20 x 20 x 1.6 mm, 2 layer |
| Direct Hall-PCB target | 2 | Mill-Max 856-10-012-30-051000 |
| Short 12-way FPC | 2 | 1.0 mm pitch, 0.3 mm reinforced same-side tails; length selected from assembled CAD |
| M2 heat-set insert | 4 | Short brass insert selected for actual wall thickness |
| M2 nonmagnetic screw | 4 | 304 stainless, length finalized after fit check |
| Asymmetric perimeter key set | 2 | Integral printed/POM carrier datum |
| Poron pad | 8 | 4701-30, 4 x 4 x 0.8 mm |
| 4 x 2 mm N35 magnet | 0 first build | Optional only after Hall testing |

## Files and manufacturing boundary

- `Symm60HE-fixed-tent-pogo-module.FCStd`: editable, separate-body source
- `Symm60HE-fixed-tent-pogo-module.step`: assembled Fusion 360 handoff
- `dimensions.json`: controlled dimensions and body inventory
- `SHA256SUMS.txt`: hashes of the editable source, STEP handoff and dimensions
- `generated/*.stl`: inspection/printing references, not final production STLs

Before machining or printing a final case, insert the real Mill-Max 854/856
STEP models, confirm connector land orientation from received parts, assign
actual heat-set inserts and screw lengths, and run an interference check with
the full PCB/plate/keycap assembly. The current geometry is a detailed
prototype mechanism, not physical fit proof.

The keyboard itself is suspended only from eight plate-side gasket tabs: four
outer locations and four centre-side locations. There are no top/bottom gasket
tabs and no gasket mount on either Hall PCB.
