# Symm60HE image gallery

These images are generated from the current KiCad boards, split plate/gasket DXFs,
and OpenSCAD case. They are not conceptual renders.

## Complete overview

- `00-complete-gallery.png`

## PCBs

- `pcb-left-top.png`
- `pcb-left-bottom.png`
- `pcb-right-top.png`
- `pcb-right-bottom.png`
- `pcb-daughterboard-top.png`
- `pcb-daughterboard-bottom.png`
- `pogo-left-spring-module-top.png`
- `pogo-left-spring-module-bottom.png`
- `pogo-right-spring-module-top.png`
- `pogo-right-spring-module-bottom.png`

The KiCad top/bottom labels describe the physical side being viewed. The Hall
sensors, muxes, and FFC connectors are on the bottom of the two keyboard
halves; the daughterboard's MCU and support components are on its top.

On the daughterboard, J2's cable opening faces the left outside edge and J3's
cable opening faces the right outside edge. The four spring-module images are
individual views of the two small floating pogo PCBs used by the Neo variant.

## Plates and gasket

- `plate-wkl.png`
- `plate-wklbs2.png`
- `plate-wklarrows.png`
- `plate-wklbs2arrows.png`
- `plate-universal.png`
- `gasket-pads.png`

Every plate image is an exploded view of two independent fabrication files;
the visible centre gap is added only to make the split unmistakable. It is not
a dimensional change to either DXF. Cut an upper and lower set of the six
discrete gasket pads from 1.5 mm Poron.

## Regeneration

`tools/render_current_pcbs.py` uses KiCad's native `pcb render` command for the
current PCB files. `tools/render_gallery.py` renders the DXF images and rebuilds
the contact sheet.
