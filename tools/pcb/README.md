# PCB preparation tools

This folder contains board mutation, routing repair, panelization, and
fabrication-preparation commands. Many of these commands alter KiCad sources in
place; use the repository-level `build.sh` for the validated production order.

## Repairing a derived board

Moving the LEDs into the switches' south RGB pockets changed what the
fixed-layout boards inherit, so their finishing pass now has tools for the
kinds of damage that causes. Each takes a board and a DRC report, and each is
meant to be followed by `repair_open_routes.py` and another DRC:

- `resync_zone_apertures.py` — move the pours' copies of the LED apertures to
  where the LEDs actually are. A footprint carries its Edge.Cuts with it; the
  hole cloned into the zone outline does not.
- `drop_orphan_copper.py` — remove copper on nets a layout has left with fewer
  than two pads. It cannot connect anything and reappears as a dangling run in
  every later report.
- `join_ground_islands.py` — tie stranded GND pads back to the plane, using the
  copper that is actually there and the fewest vias.
- `rip_around_open.py`, `rip_around_holes.py`, `rip_rule_offenders.py` — give a
  finding somewhere to move to: a window around an open the router cannot
  reach, a window around a drill the copper sits on, or the shorter piece of a
  clearance pair.
- `restore_open_nets.py` — undo a rip one net at a time, for the nets the
  router could not put back. Rolling the whole board back would discard the
  repairs that did work.
- `nudge_clearance.py` — bend a trace a few microns clear. On a full board a
  gap short by 3 um is not a routing problem, and ripping the trace only puts
  it back where it was.
- `tidy_via_joints.py` — merge vias that land on each other and pull track ends
  onto the via they are meant to reach.
