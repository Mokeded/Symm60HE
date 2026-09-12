#!/usr/bin/env python3
"""Build one connected, mouse-bite panel from the two keyboard halves.

The source boards remain the authoritative electrical designs.  The panel has
uniquely-prefixed references and net names so KiCad does not create false
cross-board ratsnest connections.  A routed 5 mm perimeter rail and 5 mm tabs
make the result one connected PCB while preserving each sculpted board edge.
"""
from copy import deepcopy
from pathlib import Path
import shutil

from shapely.affinity import translate as translate_geom
from shapely.geometry import LineString, Polygon, box
from shapely.ops import polygonize, unary_union

from sexp import Sym, dumps, find, first, loads, newuuid, set_uuids

ROOT = Path(__file__).resolve().parent.parent
PCB = ROOT / "pcb"
OUT = PCB / "Symm60HE-Panel.kicad_pcb"
GAP = 3.2
BOARD_GAP = 2.0
RAIL = 5.0
TAB_W = 5.0
MOUSE_D = 0.5
MOUSE_PITCH = 0.75


def edge_polygon(board):
    lines = []
    for item in find(board, "gr_line"):
        layer = first(item, "layer")
        if not layer or layer[1] != "Edge.Cuts":
            continue
        a, b = first(item, "start"), first(item, "end")
        lines.append(LineString([(float(a[1]), float(a[2])),
                                 (float(b[1]), float(b[2]))]))
    polys = list(polygonize(lines))
    if not polys:
        raise RuntimeError("board has no closed line-segment outline")
    return max(polys, key=lambda p: p.area)


def translate_tree(node, dx, dy):
    """Translate absolute coordinate records in a top-level board item."""
    if not isinstance(node, list):
        return
    if node and node[0] in ("at", "start", "end", "center", "mid", "xy") and len(node) >= 3:
        try:
            node[1] = round(float(node[1]) + dx, 6)
            node[2] = round(float(node[2]) + dy, 6)
        except (TypeError, ValueError):
            pass
    for child in node[1:]:
        translate_tree(child, dx, dy)


def translate_item(item, dx, dy):
    # Footprint children are library-local; only its placed origin is absolute.
    if item[0] == "footprint":
        at = first(item, "at")
        at[1] = round(float(at[1]) + dx, 6)
        at[2] = round(float(at[2]) + dy, 6)
    else:
        translate_tree(item, dx, dy)


def remap_item_nets(item, code_map, prefix):
    if not isinstance(item, list):
        return
    if item and item[0] == "net" and len(item) >= 2:
        old = int(item[1]) if str(item[1]).lstrip("-").isdigit() else None
        if old is not None:
            item[1] = code_map.get(old, old)
        elif item[1]:
            # KiCad 10 stores net names directly instead of using a root-level
            # integer net table.
            item[1] = f"/{prefix}/{item[1]}"
        if len(item) >= 3 and item[2]:
            item[2] = f"/{prefix}/{item[2]}"
    for child in item[1:]:
        remap_item_nets(child, code_map, prefix)


def prefix_reference(fp, prefix):
    for node in fp:
        if not isinstance(node, list):
            continue
        if node and node[0] == "property" and len(node) > 2 and node[1] == "Reference":
            node[2] = f"{prefix}-{node[2]}"
        elif node and node[0] == "fp_text" and len(node) > 2 and node[1] == "reference":
            node[2] = f"{prefix}-{node[2]}"


def strip_zone_fill(zone):
    zone[:] = [node for node in zone
               if not (isinstance(node, list) and node and
                       node[0] in ("filled_polygon", "fill_segments"))]


def ring_lines(ring):
    coords = list(ring.coords)
    result = []
    for a, b in zip(coords, coords[1:]):
        result.append([Sym("gr_line"), [Sym("start"), round(a[0], 5), round(a[1], 5)],
                       [Sym("end"), round(b[0], 5), round(b[1], 5)],
                       [Sym("stroke"), [Sym("width"), 0.05], [Sym("type"), Sym("default")]],
                       [Sym("layer"), "Edge.Cuts"], newuuid()])
    return result


def x_edges(poly, y):
    hit = poly.intersection(LineString([(-1e4, y), (1e4, y)]))
    xs = []
    for geom in (hit.geoms if hasattr(hit, "geoms") else (hit,)):
        xs.extend(p[0] for p in getattr(geom, "coords", ()))
    return min(xs), max(xs)


def y_edges(poly, x):
    hit = poly.intersection(LineString([(x, -1e4), (x, 1e4)]))
    ys = []
    for geom in (hit.geoms if hasattr(hit, "geoms") else (hit,)):
        ys.extend(p[1] for p in getattr(geom, "coords", ()))
    return min(ys), max(ys)


def make_mouse_template(_boards):
    module = loads((ROOT / "Symm60HE_Project.pretty" /
                    "MountingHole_2.2mm_M2_NPTH.kicad_mod").read_text())
    body = [node for node in module[2:]
            if not (isinstance(node, list) and node and
                    node[0] in ("version", "generator", "generator_version"))]
    return [Sym("footprint"), "MouseBite_0.5mm",
            [Sym("layer"), "F.Cu"], newuuid(), [Sym("at"), 0, 0]] + body


def make_library_template(filename, name):
    module = loads((ROOT / "Symm60HE_Project.pretty" / filename).read_text())
    body = [deepcopy(node) for node in module[2:]
            if not (isinstance(node, list) and node and
                    node[0] in ("version", "generator", "generator_version"))]
    return [Sym("footprint"), name, [Sym("layer"), first(module, "layer")[1]],
            newuuid(), [Sym("at"), 0, 0]] + body


def placed_feature(template, x, y, reference):
    fp = deepcopy(template)
    first(fp, "at")[1:3] = [round(x, 5), round(y, 5)]
    for node in find(fp, "property"):
        if len(node) > 2 and node[1] == "Reference":
            node[2] = reference
    set_uuids(fp)
    return fp


def mouse_hole(template, x, y, index):
    fp = deepcopy(template)
    fp[1] = "MouseBite_0.5mm"
    at = first(fp, "at")
    at[1:3] = [round(x, 5), round(y, 5)]
    for node in list(fp):
        if isinstance(node, list) and node and node[0].startswith("fp_"):
            fp.remove(node)
        elif isinstance(node, list) and len(node) > 2 and node[0] == "property":
            if node[1] == "Reference":
                node[2] = f"MB{index}"
            elif node[1] == "Value":
                node[2] = "MOUSE_BITE_0.5MM"
    for pad in find(fp, "pad"):
        first(pad, "size")[1:3] = [MOUSE_D, MOUSE_D]
        drill = first(pad, "drill")
        drill[1:] = [MOUSE_D]
    set_uuids(fp)
    return fp


def add_break_row(rows, centre, horizontal=True):
    values = [-2, -1, 0, 1, 2]
    if horizontal:
        rows.extend((centre[0] + value * MOUSE_PITCH, centre[1]) for value in values)
    else:
        rows.extend((centre[0], centre[1] + value * MOUSE_PITCH) for value in values)


def main():
    source_specs = [
        ("L", PCB / "Symm60HE-Left.kicad_pcb"),
        ("R", PCB / "Symm60HE-Right.kicad_pcb"),
    ]
    raw = [(prefix, loads(path.read_text()), path) for prefix, path in source_specs]
    left_poly, right_poly = [edge_polygon(board) for _, board, _ in raw]
    # Stack the two halves to avoid the previous 336 mm-long panel.  This is an
    # in-plane translation only, so bottom-side component rotations and CPL
    # coordinates remain straightforward for assembly.
    right_dx = left_poly.bounds[0] - right_poly.bounds[0]
    right_dy = left_poly.bounds[3] + BOARD_GAP - right_poly.bounds[1]
    offsets = {"L": (0.0, 0.0), "R": (right_dx, right_dy)}
    polys = {"L": left_poly,
             "R": translate_geom(right_poly, xoff=right_dx, yoff=right_dy)}

    # Continuous perimeter frame, with routed air gaps around each PCB except
    # where the rectangles below deliberately form breakaway tabs.
    bounds = unary_union(list(polys.values())).bounds
    outer = box(bounds[0] - GAP - RAIL, bounds[1] - GAP - RAIL,
                bounds[2] + GAP + RAIL, bounds[3] + GAP + RAIL)
    inner = box(bounds[0] - GAP, bounds[1] - GAP,
                bounds[2] + GAP, bounds[3] + GAP)
    frame = outer.difference(inner)
    tabs = []
    break_rows = []
    top_inner = bounds[1] - GAP
    bottom_inner = bounds[3] + GAP

    xmin, _, xmax, _ = bounds
    tab_xs = tuple(xmin + (xmax - xmin) * fraction for fraction in (0.23, 0.50, 0.77))

    # Three top tabs, three inter-board tabs and three bottom tabs provide a
    # short load path through the stacked panel.
    for x in tab_xs:
        top, bottom = y_edges(polys["L"], x)
        tabs.append(box(x - TAB_W/2, top_inner - 0.2,
                        x + TAB_W/2, top + 0.6))
        add_break_row(break_rows, (x, top), horizontal=True)
        lower_top, _ = y_edges(polys["R"], x)
        tabs.append(box(x - TAB_W/2, bottom - 0.6,
                        x + TAB_W/2, lower_top + 0.6))
        add_break_row(break_rows, (x, (bottom + lower_top) / 2), horizontal=True)
        _, lower_bottom = y_edges(polys["R"], x)
        tabs.append(box(x - TAB_W/2, lower_bottom - 0.6,
                        x + TAB_W/2, bottom_inner + 0.2))
        add_break_row(break_rows, (x, lower_bottom), horizontal=True)

    # One side-rail tab on each side of each half prevents twisting during
    # transport and reflow without over-perforating the keymap edge.
    left_inner = bounds[0] - GAP
    right_inner = bounds[2] + GAP
    for poly in (polys["L"], polys["R"]):
        y = (poly.bounds[1] + poly.bounds[3]) / 2
        left, right = x_edges(poly, y)
        tabs.append(box(left_inner - 0.2, y - TAB_W/2,
                        left + 0.6, y + TAB_W/2))
        add_break_row(break_rows, (left, y), horizontal=False)
        tabs.append(box(right - 0.6, y - TAB_W/2,
                        right_inner + 0.2, y + TAB_W/2))
        add_break_row(break_rows, (right, y), horizontal=False)

    material = unary_union([frame] + list(polys.values()) + tabs).buffer(0)
    if material.geom_type != "Polygon":
        raise RuntimeError(f"panel material is not one connected polygon: {material.geom_type}")

    # Use the left board's stackup/setup as the panel header.
    left_board = raw[0][1]
    object_heads = {"footprint", "segment", "via", "arc", "zone",
                    "gr_line", "gr_arc", "gr_rect", "gr_circle", "gr_poly",
                    "gr_text", "gr_text_box", "image"}
    body = [deepcopy(item) for item in left_board[1:]
            if not (isinstance(item, list) and item and
                    (item[0] in object_heads or item[0] == "net"))]
    if body and isinstance(body[-1], list) and body[-1][0] == "embedded_fonts":
        embedded = body.pop()
    else:
        embedded = [Sym("embedded_fonts"), Sym("no")]

    panel_items = []
    net_decls = [[Sym("net"), 0, ""]]
    next_code = 1
    parsed_for_template = []
    for prefix, board, path in raw:
        dx, dy = offsets[prefix]
        parsed_for_template.append((board, dx, dy, prefix))
        declarations = [item for item in board if isinstance(item, list) and item and
                        item[0] == "net" and len(item) >= 3]
        code_map = {0: 0}
        for declaration in declarations:
            old = int(declaration[1])
            if old == 0:
                continue
            code_map[old] = next_code
            net_decls.append([Sym("net"), next_code,
                              f"/{prefix}/{declaration[2]}"])
            next_code += 1
        for item in board[1:]:
            if not isinstance(item, list) or not item or item[0] not in object_heads:
                continue
            if item[0].startswith("gr_") and first(item, "layer") and first(item, "layer")[1] == "Edge.Cuts":
                continue
            copied = deepcopy(item)
            # Retain and translate the source boards' already-verified filled
            # polygons. The verification pass refills them again, but keeping
            # the fill here also makes the generated panel connected when it
            # is opened or checked before that pass.
            translate_item(copied, dx, dy)
            remap_item_nets(copied, code_map, prefix)
            if copied[0] == "footprint":
                prefix_reference(copied, prefix)
            set_uuids(copied)
            panel_items.append(copied)

    for ring in [material.exterior] + list(material.interiors):
        panel_items.extend(ring_lines(ring))
    template = make_mouse_template(parsed_for_template)
    panel_items.extend(mouse_hole(template, x, y, i + 1)
                       for i, (x, y) in enumerate(break_rows))
    fid_template = make_library_template("Fiducial_1mm_BCu.kicad_mod",
                                         "Fiducial_1mm_BCu")
    tool_template = make_library_template("ToolingHole_2mm_NPTH.kicad_mod",
                                          "ToolingHole_2mm_NPTH")
    ox0, oy0, ox1, oy1 = outer.bounds
    fiducials = ((ox0 + 3.85, oy0 + 3.85),
                 (ox1 - 3.85, oy0 + 3.85),
                 (ox0 + 3.85, oy1 - 3.85))
    tooling = ((ox0 + RAIL / 2, oy0 + (oy1 - oy0) * 0.30),
               (ox1 - RAIL / 2, oy0 + (oy1 - oy0) * 0.30),
               (ox0 + RAIL / 2, oy0 + (oy1 - oy0) * 0.70),
               (ox1 - RAIL / 2, oy0 + (oy1 - oy0) * 0.70))
    panel_items.extend(placed_feature(fid_template, x, y, f"FID{i + 1}")
                       for i, (x, y) in enumerate(fiducials))
    panel_items.extend(placed_feature(tool_template, x, y, f"TH{i + 1}")
                       for i, (x, y) in enumerate(tooling))
    panel = [Sym("kicad_pcb")] + body + net_decls + panel_items + [embedded]
    OUT.write_text(dumps(panel) + "\n")
    shutil.copy2(PCB / "Symm60HE-Left.kicad_pro", PCB / "Symm60HE-Panel.kicad_pro")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"panel size {outer.bounds[2]-outer.bounds[0]:.2f} x "
          f"{outer.bounds[3]-outer.bounds[1]:.2f} mm")
    print(f"mouse-bite drill count {len(break_rows)} across {len(break_rows)//5} break rows")
    print(f"global fiducials {len(fiducials)}; tooling holes {len(tooling)}")


if __name__ == "__main__":
    main()
