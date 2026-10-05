# Symm60HE

Symmetrical Hall-effect Alice keyboard derived from FN40HE. The production
design uses two keyboard halves connected by 12-conductor FFCs to one compact
AT32F405 daughterboard.

This tree intentionally contains only the files used to build or manufacture
the current ribbon-connected PCBs, plates, populated 3D reference assembly and
firmware. Historical routing iterations, pogo concepts, renders, caches and
intermediate CAD meshes were removed from this directory.

## Authoritative PCB projects

- `pcb/Symm60HE-Panel.kicad_pro`: universal left/right customer panel.
- `pcb/Symm60HE-Daughterboard.kicad_pro`: controller daughterboard.
- `pcb/variants/layouts/<layout>/*-Panel.kicad_pro`: eight fixed-layout
  customer panels.

The `Symm60HE-Left.kicad_pcb`, `Symm60HE-Right.kicad_pcb` and fixed-layout
`*-Left.kicad_pcb`/`*-Right.kicad_pcb` files are retained as mechanical and
generator inputs. The matching `*-Panel` project is the electrical and
manufacturing authority for each pair.

Current fabrication packages are under:

- `release/jlcpcb/`
- `release/layout-pcbs/`

## Plate sets

Manufacture plates from 1.5 mm POM. `plate/` contains a left/right plate pair
and one matching eight-pad Poron gasket DXF for every PCB layout:

| Layout stem | Left bottom row | Right bottom row | Backspace |
|---|---|---|---|
| `wkl` | two 1.5u | standard | split |
| `wkl-left-arrows-right` | two 1.5u | arrows | split |
| `three-key-left-wkl-right` | three 1u | standard | split |
| `wklarrows` | three 1u | arrows | split |
| `wklbs2` | two 1.5u | standard | 2u |
| `wkl-left-arrows-right-bs2` | two 1.5u | arrows | 2u |
| `three-key-left-wkl-right-bs2` | three 1u | standard | 2u |
| `wklbs2arrows` | three 1u | arrows | 2u |
| `universal` | all supported positions | all supported positions | both |

See `plate/README.md` for fabrication and mounting details.

## 3D reference assembly

`case/fusion360/` contains the final editable FreeCAD/Fusion handoff, combined
STEP assembly, separate named component STEP bodies, exact 1.5 mm plates,
verified switch and keycap references, and the source component models needed
to rebuild them. Manufacturing panel rails and mouse-bite tabs are not part of
the case assembly; the 3D reference represents the two depanelized halves.

The locked vertical datum is 5.00 mm from plate top to PCB top.

## Firmware

`firmware/libhmk/` is the Symm60HE firmware source. The current AT32F405 target
is selected by the `symm60he` PlatformIO environment. Distributable firmware
outputs are copied to `firmware/build/`.

## Rebuild

Requirements include Python 3, KiCad 10 CLI/Python, OpenSCAD, FreeCAD command
line tools and PlatformIO.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./build.sh
```

The build regenerates all nine plate sets, the populated 3D reference, the
universal and fixed-layout fabrication packages, validation reports and the
current firmware binaries. It does not regenerate historical prototypes.

## Licensing and provenance

GPLv3. See `LICENSE`, `NOTICE.md` and the model provenance files under
`case/fusion360/models/`.
