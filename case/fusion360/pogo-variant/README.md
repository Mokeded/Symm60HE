# Magnetic-contact mechanical reference

This directory retains the first connector-coupon cradle. The current rebuilt
assembly is `../pogo-neo/Symm60HE-Neo-Pogo-Reference.FCStd`; its detailed
connector mechanism is in `../tenting-solution/`.

`Symm60HE-pogo16-tent-cradle.FCStd` is the editable source and
`Symm60HE-pogo16-tent-cradle.step` is its Fusion 360 handoff. The files contain
separate bodies for the central controller reference, independently angled
left/right spring wings, connector envelopes, target-board planes, guide/key
pins, hard stops, Poron pads, and provisional magnet envelopes.

The two wings are parallel to their respective 3 degree keyboard-half planes.
This avoids the impossible constraint of asking one flat rigid daughterboard
to mate normally to both sides of a tented assembly. A short fixed soldered
harness connects each wing to the central controller in the prototype; a
rigid-flex controller assembly is the later single-part alternative.

The hard stops establish 6.0 mm board-to-board spacing and 0.5 mm nominal
compression for the selected Mill-Max 855/857 connector pair. Magnets do not
perform alignment. The two 2.0 mm guides and asymmetric 2.6 mm key do that.

Every magnet body is tagged `DNP_Until_Hall_Test`. Populate none until a fully
assembled measurement establishes an acceptable Hall-sensor exclusion volume.
If the sensor test fails, use the same carrier with nonmagnetic M2 screws or
snap latches instead.

## One-piece serpentine alternative

`Symm60HE-serpentine-pogo-daughterboard.step` is the 0.8 mm two-layer option-2
board reference.  It supersedes the separate rigid spring wings for the next
qualification fixture: the central controller island, routed compliant arms,
and both spring-connector lands are one FR-4 part.  Import that STEP as a new
Fusion 360 component and constrain the central island and connector lands; do
not clamp the two S-shaped moving spans.

This STEP is a placement reference, not a validated flex simulation.  The
intended six-degree tent displacement, connector compression, hard-stop height,
and Hall-sensor response still require a physical coupon/fixture test before the
857 target connectors are committed to the keyboard halves.
