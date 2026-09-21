# Symm60HE design browser

This directory is the human-facing map for the repository. Large source,
manufacturing and CAD files remain in their single canonical locations so a
change cannot silently leave a duplicate out of date.

## Choose a connection system

| Connection | What it contains | Manufacturing status |
|---|---|---|
| [Ribbon cable](ribbon/) | Universal PCB, eight fixed-layout PCB pairs, daughterboard, plates and production files | **Current prototype-order candidate** |
| [Pogo](pogo/) | Pogo16 connector coupon and two older pogo architectures | Prototype or archived only |

## Other project areas

- [Matching plates and gasket pads](plates/)
- [3D and Fusion-compatible models](3d-models/)
- [Firmware and selectable layout profiles](firmware/)
- [PCB and assembly image gallery](../docs/gallery/)
- [Current order checklist](../release/jlcpcb/ORDER-CHECKLIST.md)

The current keyboard is the ribbon-connected universal version. Do not order a
pogo design merely because it has historical Gerbers; each pogo page states
its validation status explicitly.
