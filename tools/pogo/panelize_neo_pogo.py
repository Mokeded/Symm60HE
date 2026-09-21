#!/usr/bin/env python3
"""Create PCBWay family panels for the five-board Neo pogo architecture.

The routed source boards stay authoritative.  This produces a two-design Hall
panel and a three-design controller/spring-module panel with unique references
and net names, routed rails, mouse-bite tabs, tooling holes, and global
fiducials on both assembly sides.
"""
from copy import deepcopy
from pathlib import Path
import shutil
import sys

from shapely.affinity import translate as translate_geom
from shapely.geometry import box
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pcb.panelize import (add_break_row, edge_polygon, make_library_template,
                      make_mouse_template, mouse_hole, placed_feature,
                      prefix_reference, remap_item_nets, ring_lines,
                      translate_item)
from sexp import Sym, dumps, first, loads, newuuid, set_uuids

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "pcb/variants/pogo-neo"
OUT = SOURCE / "panels"
GAP = 3.2
RAIL = 5.0
TAB_W = 5.0
BOARD_GAP = 2.0


def copy_board_items(base_board, sources):
    object_heads = {"footprint", "segment", "via", "arc", "zone",
                    "gr_line", "gr_arc", "gr_rect", "gr_circle", "gr_poly",
                    "gr_text", "gr_text_box", "image"}
    body = [deepcopy(item) for item in base_board[1:]
            if not (isinstance(item, list) and item and
                    (item[0] in object_heads or item[0] == "net"))]
    embedded = ([Sym("embedded_fonts"), Sym("no")])
    if body and isinstance(body[-1], list) and body[-1][0] == "embedded_fonts":
        embedded = body.pop()

    items = []
    declarations = [[Sym("net"), 0, ""]]
    next_code = 1
    for prefix, board, dx, dy in sources:
        code_map = {0: 0}
        for declaration in (item for item in board if isinstance(item, list)
                            and item and item[0] == "net" and len(item) >= 3):
            old = int(declaration[1])
            if old == 0:
                continue
            code_map[old] = next_code
            declarations.append([Sym("net"), next_code,
                                 f"/{prefix}/{declaration[2]}"])
            next_code += 1
        for item in board[1:]:
            if not isinstance(item, list) or not item or item[0] not in object_heads:
                continue
            layer = first(item, "layer")
            if item[0].startswith("gr_") and layer and layer[1] == "Edge.Cuts":
                continue
            copied = deepcopy(item)
            translate_item(copied, dx, dy)
            remap_item_nets(copied, code_map, prefix)
            if copied[0] == "footprint":
                prefix_reference(copied, prefix)
            set_uuids(copied)
            items.append(copied)
    return body, declarations, items, embedded


def panel_features(material, outer, break_rows, parsed_sources):
    items = []
    for ring in [material.exterior] + list(material.interiors):
        items.extend(ring_lines(ring))
    mouse_template = make_mouse_template(parsed_sources)
    items.extend(mouse_hole(mouse_template, x, y, index + 1)
                 for index, (x, y) in enumerate(break_rows))

    front_fid = make_library_template("Fiducial_1mm_FCu.kicad_mod",
                                      "Fiducial_1mm_FCu")
    back_fid = make_library_template("Fiducial_1mm_BCu.kicad_mod",
                                     "Fiducial_1mm_BCu")
    tooling = make_library_template("ToolingHole_2mm_NPTH.kicad_mod",
                                    "ToolingHole_2mm_NPTH")
    x0, y0, x1, y1 = outer.bounds
    fiducials = ((x0 + 3.85, y0 + 3.85),
                 (x1 - 3.85, y0 + 3.85),
                 (x0 + 3.85, y1 - 3.85))
    holes = ((x0 + RAIL / 2, y0 + (y1 - y0) * 0.30),
             (x1 - RAIL / 2, y0 + (y1 - y0) * 0.30),
             (x0 + RAIL / 2, y0 + (y1 - y0) * 0.70),
             (x1 - RAIL / 2, y0 + (y1 - y0) * 0.70))
    for index, (x, y) in enumerate(fiducials, 1):
        items.append(placed_feature(front_fid, x, y, f"FIDF{index}"))
        items.append(placed_feature(back_fid, x, y, f"FIDB{index}"))
    items.extend(placed_feature(tooling, x, y, f"TH{index}")
                 for index, (x, y) in enumerate(holes, 1))
    return items


def write_panel(name, specs, placements, tabs, project_source):
    parsed = []
    polygons = {}
    for prefix, filename in specs:
        board = loads((SOURCE / filename).read_text())
        dx, dy = placements[prefix]
        parsed.append((prefix, board, dx, dy))
        polygons[prefix] = translate_geom(edge_polygon(board), xoff=dx, yoff=dy)

    bounds = unary_union(list(polygons.values())).bounds
    inner = box(bounds[0] - GAP, bounds[1] - GAP,
                bounds[2] + GAP, bounds[3] + GAP)
    outer = box(bounds[0] - GAP - RAIL, bounds[1] - GAP - RAIL,
                bounds[2] + GAP + RAIL, bounds[3] + GAP + RAIL)
    frame = outer.difference(inner)
    tab_shapes, break_rows = tabs(polygons, inner)
    material = unary_union([frame] + list(polygons.values()) + tab_shapes).buffer(0)
    if material.geom_type != "Polygon":
        raise RuntimeError(f"{name}: disconnected panel geometry: {material.geom_type}")

    base = parsed[0][1]
    body, nets, items, embedded = copy_board_items(base, parsed)
    items.extend(panel_features(material, outer, break_rows, parsed))
    panel = [Sym("kicad_pcb")] + body + nets + items + [embedded]
    path = OUT / f"{name}.kicad_pcb"
    path.write_text(dumps(panel) + "\n")
    shutil.copy2(SOURCE / project_source, OUT / f"{name}.kicad_pro")
    print(path.relative_to(ROOT))
    print(f"  {outer.bounds[2] - outer.bounds[0]:.2f} x "
          f"{outer.bounds[3] - outer.bounds[1]:.2f} mm; "
          f"{len(break_rows) // 5} break rows")
    return path


def vertical_tab(shapes, rows, x, y0, y1, board_edge):
    shapes.append(box(x - TAB_W / 2, min(y0, y1) - 0.2,
                      x + TAB_W / 2, max(y0, y1) + 0.2))
    add_break_row(rows, (x, board_edge), horizontal=True)


def horizontal_tab(shapes, rows, x0, x1, y, board_edge):
    shapes.append(box(min(x0, x1) - 0.2, y - TAB_W / 2,
                      max(x0, x1) + 0.2, y + TAB_W / 2))
    add_break_row(rows, (board_edge, y), horizontal=False)


def hall_tabs(polygons, inner):
    left, right = polygons["LH"], polygons["RH"]
    shapes, rows = [], []
    ix0, iy0, ix1, iy1 = inner.bounds
    for fraction in (0.22, 0.50, 0.78):
        x = left.bounds[0] + (left.bounds[2] - left.bounds[0]) * fraction
        vertical_tab(shapes, rows, x, iy0, left.bounds[1], left.bounds[1])
        vertical_tab(shapes, rows, x, right.bounds[3], iy1, right.bounds[3])
    # Four rail ties on each half prevent the large Hall boards twisting.
    for poly in (left, right):
        for fraction in (0.34, 0.68):
            y = poly.bounds[1] + (poly.bounds[3] - poly.bounds[1]) * fraction
            horizontal_tab(shapes, rows, ix0, poly.bounds[0], y, poly.bounds[0])
            horizontal_tab(shapes, rows, poly.bounds[2], ix1, y, poly.bounds[2])
    return shapes, rows


def centre_tabs(polygons, inner):
    ctl, left, right = polygons["CTL"], polygons["LS"], polygons["RS"]
    shapes, rows = [], []
    ix0, iy0, ix1, iy1 = inner.bounds
    for fraction in (0.27, 0.73):
        x = ctl.bounds[0] + (ctl.bounds[2] - ctl.bounds[0]) * fraction
        vertical_tab(shapes, rows, x, iy0, ctl.bounds[1], ctl.bounds[1])
    y = (ctl.bounds[1] + ctl.bounds[3]) / 2
    horizontal_tab(shapes, rows, ix0, ctl.bounds[0], y, ctl.bounds[0])
    horizontal_tab(shapes, rows, ctl.bounds[2], ix1, y, ctl.bounds[2])
    for poly, outside in ((left, "left"), (right, "right")):
        for fraction in (0.28, 0.72):
            x = poly.bounds[0] + (poly.bounds[2] - poly.bounds[0]) * fraction
            vertical_tab(shapes, rows, x, poly.bounds[3], iy1, poly.bounds[3])
        y = (poly.bounds[1] + poly.bounds[3]) / 2
        if outside == "left":
            horizontal_tab(shapes, rows, ix0, poly.bounds[0], y, poly.bounds[0])
        else:
            horizontal_tab(shapes, rows, poly.bounds[2], ix1, y, poly.bounds[2])
    return shapes, rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "fp-lib-table").write_text(
        '(fp_lib_table\n'
        '  (lib (name "Symm60HE_Project")(type "KiCad")'
        '(uri "${KIPRJMOD}/../../../../Symm60HE_Project.pretty")'
        '(options "")(descr "Symm60HE Neo pogo panel footprints"))\n'
        ')\n')
    left = loads((SOURCE / "Symm60HE-Neo-Left-Half.kicad_pcb").read_text())
    right = loads((SOURCE / "Symm60HE-Neo-Right-Half.kicad_pcb").read_text())
    lp, rp = edge_polygon(left), edge_polygon(right)
    hall_placements = {
        "LH": (-lp.bounds[0], -lp.bounds[1]),
        "RH": (-rp.bounds[0], lp.bounds[3] - lp.bounds[1] + BOARD_GAP - rp.bounds[1]),
    }
    write_panel(
        "Symm60HE-Neo-Hall-Family-Panel",
        (("LH", "Symm60HE-Neo-Left-Half.kicad_pcb"),
         ("RH", "Symm60HE-Neo-Right-Half.kicad_pcb")),
        hall_placements, hall_tabs, "Symm60HE-Neo-Left-Half.kicad_pro")

    controller = loads((SOURCE / "Symm60HE-Neo-Controller.kicad_pcb").read_text())
    cp = edge_polygon(controller)
    centre_placements = {
        "CTL": (-cp.bounds[0], -cp.bounds[1]),
        "LS": (0.0, 30.0),
        "RS": (37.0, 30.0),
    }
    write_panel(
        "Symm60HE-Neo-Centre-Family-Panel",
        (("CTL", "Symm60HE-Neo-Controller.kicad_pcb"),
         ("LS", "Symm60HE-Neo-Left-SpringModule.kicad_pcb"),
         ("RS", "Symm60HE-Neo-Right-SpringModule.kicad_pcb")),
        centre_placements, centre_tabs, "Symm60HE-Neo-Controller.kicad_pro")


if __name__ == "__main__":
    main()
