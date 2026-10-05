# Symm60HE compact daughterboard reroute

Date: 2026-10-03

## Result

The manufacturing KiCad project is:

`Symm60HE-Daughterboard`

This completed design retains every footprint position, orientation, board side,
pad number, pad net, FFC conductor assignment, USB datum, and M2 mounting-hole
centre from the verified FPC-matched routing. It reduces only the unused
perimeter and rebuilds the ground implementation and eligible local routes.

## Compact mechanical envelope

| Metric | Prior | Compact reroute |
| --- | ---: | ---: |
| Nominal outline | 50.0 x 31.0 mm | 49.5 x 29.2 mm |
| Rectangular envelope | 1550.0 mm^2 | 1445.4 mm^2 |
| Envelope reduction | - | 6.75% |
| Corner radius | 1.0 mm | 0.5 mm |

The USB-side board edge, USB connector centre, four M2 mount centres, and FFC
connector centres are unchanged. The 0.5 mm corners allow the shorter upper
edge to clear the two upper M2 holes while retaining the board's 0.20 mm
copper/hole-to-edge rules. KiCad DRC confirms the new perimeter has no edge or
hole-clearance errors.

This is the smallest verified outline found without moving case-defined M2
holes, the USB cutout datum, or either FFC connector. A 46.8 x 29.2 mm
experiment required moving both FFC connectors inward and produced real pad,
via, track, and mechanical-pad conflicts. That experiment was rejected and is
not included as an editable project.

## Routing cleanup

| Metric | Prior | Compact reroute |
| --- | ---: | ---: |
| Routed segments | 721 | 547 |
| Routed length | 1453.377 mm | 1213.214 mm |
| Total vias | 74 | 73 |
| Explicit GND segments | 174 | 0 |
| GND stitching vias | 6 | 5 |
| In-pad vias | 0 | 0 |

Both external GND pours reach all 47 GND pads, so the former 174-segment GND
trace network was redundant. It was removed only after refill/connectivity
testing proved every GND pad remained in one connected component. One of the
six old GND stitching vias was then removed; each of the five retained vias is
required to preserve the filled contours, filled area, and complete pad
connectivity.

The reroute also:

- compacted the remaining eligible B.Cu VBUS walk into a shorter parallel
  lane;
- aligned the remaining eligible CC2 path with a nearby route;
- retained the minimum-via signal topology where no shorter clearance-safe
  replacement existed;
- removed all removable same-net loops and redundant vias;
- eliminated free-copper acute hooks and unlanded 90-degree corners; and
- kept the established 0/45-degree route geometry.

## Trace widths and future routing defaults

The project contains functional netclasses so new manual traces use the same
width policy as the completed keyboard halves:

| Role | Netclass width | Applied routing |
| --- | ---: | --- |
| Signal / USB / RGB / crystal | 0.20 mm | 0.20 mm |
| ADC and mux/control | 0.25 mm | all corresponding tracks at 0.25 mm |
| +3V3A | 0.30 mm | all 37 tracks at 0.30 mm |
| +3V3D | 0.30 mm | 49 tracks at 0.30 mm, 9 clearance neck-downs at 0.20 mm |
| GND | 0.30 mm | pour-based; no explicit GND tracks remain |
| VBUS | 0.40 mm | 30 tracks at 0.40 mm, 15 clearance neck-downs at 0.20 mm |
| VBUS_IN | 0.40 mm | 5 tracks at 0.40 mm, 3 USB-pad neck-downs at 0.20 mm |

The narrower power sections are intentional local neck-downs beside USB,
fine-pitch, or tightly spaced copper. Widening those sections without moving
components causes reproducible clearance violations; the wider trunks are
used everywhere the checked geometry permits them.

## Electrical and geometric validation

- KiCad PCB DRC: zero electrical/clearance errors and zero unconnected pads.
- DRC retains only four inherited local-footprint/library mismatch warnings on
  the four M2 NPTH footprints.
- Schematic ERC: zero violations.
- FPC contract: all 16 cleaned fixed-layout halves checked with zero
  mismatches; left remains daughter `J2 N -> JL1 13-N`, right remains daughter
  `J3 N -> JR1 N`.
- Footprint positions, rotations, sides, pad numbers, and pad nets: exact match
  to the prior FPC-matched daughterboard.
- Schematic and captured-symbol files: byte-identical to the prior derivative.
- GND connectivity: 47/47 pads connected, five retained stitching vias.
- Redundant-route audit: zero removable atomic edges or vias.
- Acute-hook audit: zero.
- Unlanded right-angle audit: zero.
- Conservative parallel-route beautification audit: no candidate remains.
- In-pad via audit: zero.

## Preview

The route-only before/after comparison is:

`daughterboard-previews/compact-rerouted/paired/daughterboard-before-after-routing.png`

Copper pours are hidden in that preview for route clarity; the saved compact
board contains refilled GND zones on both external copper layers.
