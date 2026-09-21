# Ribbon-cable PCB family

The ribbon family is the current, build-verified design. Each keyboard half
keeps its Hall sensors and analog multiplexers locally and sends five
multiplexed analog channels through a 12-way FFC to the centre daughterboard.

## PCB choices

- [Universal, firmware-selectable PCB](universal/) — fully populates every
  supported Hall sensor and LED position; select one of four layouts in
  firmware. This is the primary manufacturing candidate.
- [Fixed-layout PCB pairs](fixed-layouts/) — separate left/right boards for
  eight physical permutations, each with only its required switch positions.

## Shared daughterboard

- [KiCad source](../../pcb/Symm60HE-Daughterboard.kicad_pcb)
- [Current manufacturing order](../../release/jlcpcb/Symm60HE-Daughterboard/)
- [Gerber archive](../../release/jlcpcb/Symm60HE-Daughterboard-Gerbers.zip)
- [Populated 3D model](../../case/fusion360/Symm60HE-DaughterboardPCBComponents.step)

Use the [prototype-order checklist](../../release/jlcpcb/ORDER-CHECKLIST.md)
before submitting either board order.
