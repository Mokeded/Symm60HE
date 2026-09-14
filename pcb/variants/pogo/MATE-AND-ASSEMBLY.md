# How the 854/856 pair actually mates, and what that costs at assembly

Everything below is measured off the generated meshes of
`case/fusion360/Symm60HE-case-reference-assembly`, not retyped from a
datasheet. Regenerate with:

```sh
./.venv/bin/python tools/pogo_mate_geometry.py        # the numbers
./.venv/bin/python tools/render_pogo_mate_detail.py   # docs/img/37-39
xvfb-run -a ./.venv/bin/python tools/render_pogo_mate_3d.py  # docs/img/40-41
```

| Figure | Shows |
|---|---|
| `docs/img/37-pogo-mate-section.png` | the whole 12-contact pair in section, both boards |
| `docs/img/38-pogo-mate-contact-detail.png` | one contact, traced from the vendor STEP |
| `docs/img/39-pogo-mate-landing-zone.png` | the contact's slip budget against the aperture float |
| `docs/img/40-pogo-mate-3d-seated.png` | the seated pair |
| `docs/img/41-pogo-mate-3d-exploded.png` | the same pair pulled apart |

## Measured stack

| | mm |
|---|---|
| Board to board, 854 seating face (module PCB top) to 856 seating face (Hall PCB underside) | **5.0000** |
| 854 free height, tail tip to plunger tip | 4.2164 |
| 854 seated height | 3.9595 |
| Preload | **0.2569** |
| Travel left of the 1.016 mm stroke | **0.7591** |
| 854 housing face to 856 housing face | 0.6058 |
| Plunger proud of the 854 housing face | 0.3016 seated, 0.5585 free |
| 856 pillar proud of its housing face | 0.3062 |
| Plunger tip diameter | 0.6857 |
| 856 contact flat diameter | 0.6526 |
| 856 pillar outside diameter | 0.8049 |
| Pillar chamfer, 0.8049 down to 0.6526 | over 0.060 axial |

The 5.0000 mm and the 0.2569/0.7591 preload and travel confirm the reference
assembly is built exactly as `CONNECTOR-AND-TENTING.md` specifies. The 854's
tails pass through the 1.2 mm module PCB, so its 4.2164 mm envelope is not all
above-board; the number that matters to the case is the 5.0000 mm between the
two board faces.

## The part that matters for dropping PCBs into the case

**This pair does not self-align.** It is a precision board-to-board connector:
a flat plunger butting a flat pillar. The only lead-in anywhere on either half
is the 0.060 mm chamfer on the rim of each 856 pillar. Radial misalignment
before a plunger tip walks off its pillar is

```
(0.8049 - 0.6857) / 2 = 0.0596 mm
```

The kernel aperture gives each spring module **0.4 mm of X/Y clearance per
side**. That is 6.7x further than a contact can follow. The aperture's
asymmetric perimeter keys therefore have to *locate* the module, not merely
retain it — if that 0.4 mm is ever positional slop rather than fit clearance,
the joint is out of tolerance before the boards touch.

Three further consequences:

1. **The approach is blind.** At the working stack the two housings are
   0.6058 mm apart. A free plunger stands 0.5585 mm proud and a pillar
   0.3062 mm, so the contacts first meet about 0.87 mm before the boards reach
   their working separation. Nothing on either connector guides the boards
   over that last 0.87 mm; the case has to have finished aligning them first.
2. **The failure is quiet, not violent.** A plunger that misses its pillar
   entirely lands on the 856 housing face, and 0.5585 mm of free protrusion is
   less than the 0.6058 mm gap, so it simply never touches. Expect a dead
   channel, not a bent pin. This is why the continuity check on pins 1-12
   before first power is not optional.
3. **Theta matters as much as X/Y.** The contact row is 13.97 mm end to end.
   0.0596 mm of slip at the outermost contact is 0.49 degrees of rotation about
   the row centre, so the aperture has to control rotation to well inside half
   a degree.

## What would make it an easy fit

In rough order of how much they buy:

- **Take the bare hard-gold pad option already noted in
  `CONNECTOR-AND-TENTING.md`.** Mill-Max 854 plungers are rated to mate
  against flat gold pads. A 1.5 mm pad in place of the 856 gives roughly
  +/-0.4 mm of landing, which finally matches the aperture float instead of
  fighting it, and deletes two parts per keyboard. It needs a coupon first:
  the trade is the 856's harder wear surface and its alignment housing.
- **Add a real lead-in to the case, since the connector has none.** A tapered
  entry on the kernel aperture plus one dowel-and-slot pair between the Hall
  PCB and the kernel, sized to land the boards inside +/-0.05 mm before the
  plungers reach the pillars.
- **Separate the two roles of the 0.4 mm.** Decide explicitly which aperture
  features set position and which only allow gasket-following motion, and put
  the tolerance stack for the position-setting ones in
  `case/fusion360/tenting-solution/dimensions.json`.
- **Check it on the first article.** With the boards at working separation,
  confirm all twelve contacts before relying on the fit; a 0.06 mm budget is
  not something to take on CAD alone.
