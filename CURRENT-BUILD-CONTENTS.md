# Current build contents

This directory was reduced on 2026-10-05 to the inputs, validation tools and
final outputs for the current ribbon-connected Symm60HE design.

## Retained

- Universal and eight fixed-layout combined PCB/schematic panel projects.
- Compact daughterboard project.
- Half-board mechanical/generator inputs required by plate and 3D generation.
- Current JLCPCB Gerber/BOM/CPL packages and verification reports.
- Nine plate pairs and their matching Poron gasket-pad DXFs.
- Current populated FreeCAD/Fusion/STEP reference assembly, separate named
  bodies, verified component models and Fusion import script.
- Symm60HE AT32F405 firmware source and distributable BIN/HEX/ELF artifacts.
- Only the scripts used by the supported current build and validation path.
- Git metadata, licensing, provenance and build instructions.

## Recoverable archive

Removed files were moved, not irreversibly erased, to the sibling directory:

`../Symm60HE-removed-2026-10-05-current-build-cleanup/`

That archive contains historical pogo projects/releases, retired case and
tenting concepts, rendered galleries, CAD intermediates, PlatformIO and Python
caches, obsolete reports, unused keyboard targets, and one-time routing/repair
scripts. Nothing in the supported `./build.sh` path reads from the archive.
