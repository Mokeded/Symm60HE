#!/usr/bin/env python3
"""Run the release checks against the current two-layer boards.

KiCad is authoritative for curved outlines, filled zones, copper clearance and
connectivity. The project-specific scripts independently check overlapping
multi-layout pads and the Hall-sensor/mux/ribbon net architecture.
"""
import glob
import csv
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BOARDS = ("Symm60HE-Left", "Symm60HE-Right", "Symm60HE-Daughterboard")
FAB_BOARDS = BOARDS + ("Symm60HE-Panel",)
PLATE_VARIANTS = (
    "wkl", "wklarrows", "wklbs2", "wklbs2arrows",
    "wkl-left-arrows-right", "three-key-left-wkl-right",
    "wkl-left-arrows-right-bs2", "three-key-left-wkl-right-bs2",
    "universal",
)
VENV_PYTHON = ROOT / ".venv" / ("Scripts/python.exe" if sys.platform == "win32"
                                else "bin/python")
PROJECT_PYTHON = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable


def run_project_check(label, script):
    print(f"=== {label} ===")
    result = subprocess.run([PROJECT_PYTHON, str(HERE / script)], cwd=HERE,
                            capture_output=True, text=True)
    print((result.stdout + result.stderr).rstrip())
    print(">>> ok\n" if result.returncode == 0 else ">>> FAILED\n")
    return result.returncode == 0


def find_kicad_cli():
    found = shutil.which("kicad-cli") or shutil.which("kicad-cli.exe")
    if found:
        return found
    candidates = sorted(glob.glob(
        "/opt/homebrew/Caskroom/kicad/*/KiCad/KiCad.app/Contents/MacOS/kicad-cli"),
        reverse=True)
    candidates += sorted(glob.glob(
        "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"), reverse=True)
    return candidates[0] if candidates else None


def two_layer_audit():
    sys.path.insert(0, str(HERE))
    from sexp import loads, first

    print("=== copper stackup ===")
    ok = True
    for name in BOARDS:
        board = loads((ROOT / "pcb" / f"{name}.kicad_pcb").read_text())
        copper = [item[1] for item in first(board, "layers")[1:]
                  if isinstance(item, list) and len(item) > 1 and
                  str(item[1]).endswith(".Cu")]
        good = copper == ["F.Cu", "B.Cu"]
        print(f"{name}: {', '.join(copper)}" + ("" if good else "  MISMATCH"))
        ok &= good
    print(">>> ok\n" if ok else ">>> FAILED\n")
    return ok


def kicad_drc():
    cli = find_kicad_cli()
    print("=== KiCad DRC ===")
    if not cli:
        print("kicad-cli was not found; install KiCad 10 or add it to PATH")
        print(">>> FAILED\n")
        return False
    ok = True
    with tempfile.TemporaryDirectory(prefix="symm60he-drc-") as temp:
        for name in FAB_BOARDS:
            board = ROOT / "pcb" / f"{name}.kicad_pcb"
            report = Path(temp) / f"{name}.rpt"
            result = subprocess.run(
                [cli, "pcb", "drc", "--refill-zones", "--all-track-errors",
                 "--severity-all", "--exit-code-violations", "-o", str(report),
                 str(board)], cwd=ROOT / "pcb", capture_output=True, text=True)
            output = (result.stdout + result.stderr).strip().replace("\n", " | ")
            print(f"{name}: {output}")
            report_text = report.read_text() if report.exists() else ""
            violations = re.findall(r"^\[([^]]+)\]", report_text, re.MULTILINE)
            # Board instances intentionally carry local pad/graphic edits made
            # during routing and aperture generation.  Library comparison
            # notices do not describe fabricated geometry; accept only these
            # two bookkeeping categories and never electrical/geometry errors.
            only_library_notices = (violations and set(violations).issubset({
                "lib_footprint_issues", "lib_footprint_mismatch"}))
            ok &= result.returncode == 0 or only_library_notices
    print(">>> ok\n" if ok else ">>> FAILED\n")
    return ok


def kicad_erc():
    cli = find_kicad_cli()
    print("=== KiCad ERC ===")
    if not cli:
        print("kicad-cli was not found")
        print(">>> FAILED\n")
        return False
    ok = True
    with tempfile.TemporaryDirectory(prefix="symm60he-erc-") as temp:
        for name in BOARDS:
            schematic = ROOT / "pcb" / f"{name}.kicad_sch"
            report = Path(temp) / f"{name}.rpt"
            result = subprocess.run(
                [cli, "sch", "erc", "--severity-all", "--exit-code-violations",
                 "-o", str(report), str(schematic)], cwd=ROOT / "pcb",
                capture_output=True, text=True)
            print(f"{name}: return={result.returncode}")
            ok &= result.returncode == 0
    print(">>> ok\n" if ok else ">>> FAILED\n")
    return ok


def firmware_check():
    print("=== firmware configuration/artifact ===")
    path = ROOT / "firmware/libhmk/keyboards/symm60he/keyboard.json"
    image = ROOT / "firmware/build/firmware.bin"
    try:
        data = json.loads(path.read_text())
        matrix = data["analog"]["mux"]["matrix"]
        mapped = sorted(value for row in matrix for value in row if value)
        masks = data["keyboard"]["active_key_masks"]
        good = (data["keyboard"]["num_keys"] == 69 and
                data["analog"]["mux"]["select"] == ["C1", "C2", "C3"] and
                data["analog"]["mux"]["input"] ==
                ["A3", "A4", "A5", "A6", "A2",
                 "A7", "C4", "C5", "B0", "A1"] and
                mapped == list(range(1, 70)) and
                [sum(mask) for mask in masks] == [60, 63, 59, 62] and
                image.is_file() and
                image.stat().st_size > 0)
        print(f"69 independent channels once each; active profile counts "
              f"{[sum(mask) for mask in masks]}; "
              f"firmware.bin={image.stat().st_size if image.exists() else 0} bytes")
    except (KeyError, OSError, ValueError, TypeError) as exc:
        print(exc)
        good = False
    print(">>> ok\n" if good else ">>> FAILED\n")
    return good


def release_check():
    print("=== fabrication archives ===")
    ok = True
    import zipfile
    expected_jobs = {
        "Symm60HE-Half-Panel": ("Symm60HE-Panel", None),
        # KiCad's job bounds include the 0.05 mm Edge.Cuts stroke per side.
        "Symm60HE-Daughterboard": ("Symm60HE-Daughterboard", (50.1, 31.1)),
    }
    for name, (board_name, expected_size) in expected_jobs.items():
        archive = ROOT / "release/jlcpcb" / f"{name}-Gerbers.zip"
        try:
            with zipfile.ZipFile(archive) as zipped:
                names = zipped.namelist()
                archive_good = zipped.testzip() is None and len(names) >= 9
            bom = ROOT / "release/jlcpcb" / name / f"{name}-BOM.csv"
            cpl = ROOT / "release/jlcpcb" / name / f"{name}-CPL.csv"
            bom_rows = list(csv.DictReader(bom.open()))
            positions = list(csv.DictReader(cpl.open()))
            bom_refs = {ref for row in bom_rows
                        for ref in row["Designator"].split(",")}
            cpl_refs = {row["Ref"] for row in positions}
            board = ROOT / "pcb" / f"{board_name}.kicad_pcb"
            current = archive.stat().st_mtime >= board.stat().st_mtime
            size_good = True
            if expected_size is not None:
                job = json.loads((ROOT / "release/jlcpcb" / name / "gerbers" /
                                  f"{board_name}-job.gbrjob").read_text())
                size = job["GeneralSpecs"]["Size"]
                size_good = (abs(float(size["X"]) - expected_size[0]) < 0.01 and
                             abs(float(size["Y"]) - expected_size[1]) < 0.01)
            good = (archive_good and bool(bom_rows) and bom_refs == cpl_refs and
                    all(row["LCSC Part #"] not in ("", "--")
                        for row in bom_rows) and current and size_good)
        except (KeyError, OSError, ValueError, TypeError, zipfile.BadZipFile):
            good = False
            names = []
            bom_rows = []
        print(f"{name}: {len(names)} files, {len(bom_rows)} fitted SMT BOM rows" +
              ("" if good else "  FAILED (stale or inconsistent release)"))
        ok &= good
    print(">>> ok\n" if ok else ">>> FAILED\n")
    return ok


def split_plate_audit():
    print("=== split plate fabrication files ===")
    try:
        import ezdxf
    except ImportError:
        print("ezdxf is not installed")
        print(">>> FAILED\n")
        return False
    sys.path.insert(0, str(HERE))
    from geom import KEYS
    from layouts.make_layout_pcbs import source_layout
    from shapely.geometry import LineString, Polygon, Point
    from shapely.affinity import scale as shapely_scale
    from shapely.ops import unary_union
    from mkplate import (PLATE_STANDOFFS, PLATE_STANDOFF_DIAMETER,
                         STANDOFF_BODY_RADIUS, STANDOFF_OPENING_CLEARANCE,
                         STANDOFF_EDGE_CLEARANCE, MOUNT_OPENING_CLEARANCE,
                         POM_MIN_WEB)
    from outline import (finished_plate_outline, gasket_tabs,
                         keycap_bounded_plate, keycap_core_plate,
                         keycap_plate_envelope,
                         straight_gasket_walls, PLATE_PCB_FOLLOW_MARGIN,
                         PLATE_INNER_WALL_GAP, PLATE_OUTER_WALL_X, axis_mm)
    from route import read as read_board
    from sexp import find as sexp_find, first as sexp_first, loads as sexp_loads
    ok = True
    for variant in PLATE_VARIANTS:
        sides = []
        fabrication_outlines = []
        expected_gasket_pads = []
        for side in ("left", "right"):
            path = ROOT / "plate" / f"Symm60HE-plate-{variant}-{side}.dxf"
            try:
                doc = ezdxf.readfile(path)
                auditor = doc.audit()
                outlines = list(doc.modelspace().query(
                    'LWPOLYLINE[layer=="PLATE_OUTLINE"]'))
                if len(outlines) != 1:
                    raise ValueError("expected exactly one plate outline")
                outline = Polygon([
                    (point[0], point[1])
                    for point in outlines[0].get_points("xy")
                ])
                fabrication_outlines.append(outline)
                half = side[0].upper()
                if variant == "universal":
                    keys = [key for key in KEYS if key["half"] == half]
                else:
                    build = "doe-" + source_layout(
                        variant, "Left" if half == "L" else "Right")
                    keys = [key for key in KEYS
                            if key["half"] == half and
                            build in key["builds"]]
                cap_hull = keycap_plate_envelope(keys)
                openings = list(doc.modelspace().query(
                    'LWPOLYLINE[layer=="SWITCH_CUTOUTS"]')) + list(
                    doc.modelspace().query(
                        'LWPOLYLINE[layer=="STAB_CLEARANCE"]'))
                opening_polys = [Polygon([
                    (point[0], point[1])
                    for point in entity.get_points("xy")
                ]) for entity in openings]
                mount_entities = list(doc.modelspace().query(
                    'LWPOLYLINE[layer=="STANDOFF_HOLES"]'))
                mount_polys = [Polygon([
                    (point[0], point[1])
                    for point in entity.get_points("xy")
                ]) for entity in mount_entities]
                # Flex-relief slots were removed to restore the solid plate
                # structure.  Treat any stale FLEX_CUTS entity as a failure.
                obsolete_flex = list(doc.modelspace().query(
                    'LWPOLYLINE[layer=="FLEX_CUTS"]'))
                plate_body = keycap_bounded_plate(keys)
                integral_gasket_mounts = gasket_tabs(plate_body, half)
                expected_gasket_pads.extend(
                    tab.buffer(-0.55, join_style=2)
                    for tab in integral_gasket_mounts)
                expected_outline = finished_plate_outline(half)
                # Query the actual polygon datums rather than reconstructing
                # them arithmetically.  GEOS can retain a harmless ~1e-14 mm
                # coordinate residue after the union/mirror operation; a line
                # made from the nominal decimal then misses the coincident
                # left wall even though the fabrication contour is straight.
                outer_wall_x = (plate_body.bounds[0] if half == "L" else
                                plate_body.bounds[2])
                inner_wall_x = (plate_body.bounds[2] if half == "L" else
                                plate_body.bounds[0])
                nominal_outer_wall_x = (
                    PLATE_OUTER_WALL_X if half == "L" else
                    2.0 * axis_mm - PLATE_OUTER_WALL_X)
                nominal_inner_wall_x = (
                    axis_mm - PLATE_INNER_WALL_GAP / 2.0 if half == "L" else
                    axis_mm + PLATE_INNER_WALL_GAP / 2.0)
                outer_wall_line = LineString([
                    (outer_wall_x, -1e4), (outer_wall_x, 1e4)])
                inner_wall_line = LineString([
                    (inner_wall_x, -1e4), (inner_wall_x, 1e4)])
                straight_walls_good = (
                    abs(outer_wall_x - nominal_outer_wall_x) < 1e-6 and
                    abs(inner_wall_x - nominal_inner_wall_x) < 1e-6 and
                    plate_body.boundary.intersection(outer_wall_line).length > 90.0 and
                    plate_body.boundary.intersection(inner_wall_line).length > 90.0 and
                    all(tab.intersects(outer_wall_line)
                        for tab in integral_gasket_mounts[:2]) and
                    all(tab.intersects(inner_wall_line)
                        for tab in integral_gasket_mounts[2:]))
                # Straight side rails are intentional gasket-wall geometry;
                # only the ordinary structural core is keycap-bounded.
                outside = keycap_core_plate(keys).difference(cap_hull).area
                obstacle = unary_union(opening_polys)
                minimum_web = min(
                    outline.exterior.distance(opening)
                    for opening in opening_polys)
                expected_mounts = PLATE_STANDOFFS[half]
                mount_centres = sorted(
                    (round(poly.centroid.x, 3), round(poly.centroid.y, 3))
                    for poly in mount_polys)
                expected_centres = sorted(
                    (round(x, 3), round(y, 3)) for x, y in expected_mounts)
                board_path = (
                    ROOT / "pcb" / f"Symm60HE-{'Left' if half == 'L' else 'Right'}.kicad_pcb"
                    if variant == "universal" else
                    ROOT / "pcb/variants/layouts" / variant /
                    f"Symm60HE-{variant}-{'Left' if half == 'L' else 'Right'}.kicad_pcb"
                )
                routed_pcb_outline = read_board(str(board_path))[2]
                routed_profile = straight_gasket_walls(
                    routed_pcb_outline.buffer(
                        PLATE_PCB_FOLLOW_MARGIN, join_style=2), half)
                pcb_profile_error = plate_body.symmetric_difference(
                    routed_profile).area
                board = sexp_loads(board_path.read_text())
                board_mount_centres = []
                board_mount_geometry_good = True
                mount_prefix = "MHL" if half == "L" else "MHR"
                for footprint in sexp_find(board, "footprint"):
                    reference = next((str(prop[2])
                                      for prop in sexp_find(footprint, "property")
                                      if len(prop) > 2 and
                                      str(prop[1]) == "Reference"), "")
                    if not reference.startswith(mount_prefix):
                        continue
                    at = sexp_first(footprint, "at")
                    board_mount_centres.append(
                        (round(float(at[1]), 3), round(float(at[2]), 3)))
                    pads = sexp_find(footprint, "pad")
                    geometry_good = len(pads) == 1
                    if geometry_good:
                        pad = pads[0]
                        drill = sexp_first(pad, "drill")
                        size = sexp_first(pad, "size")
                        geometry_good = (
                            str(pad[2]) == "np_thru_hole" and
                            drill is not None and size is not None and
                            abs(float(drill[1]) - PLATE_STANDOFF_DIAMETER) < 1e-6 and
                            all(abs(float(value) - PLATE_STANDOFF_DIAMETER) < 1e-6
                                for value in size[1:3]) and
                            not sexp_find(pad, "net"))
                    board_mount_geometry_good &= geometry_good
                board_mounts_good = (
                    sorted(board_mount_centres) == expected_centres and
                    len(board_mount_centres) == 4 and
                    board_mount_geometry_good)
                mounts_good = (
                    len(mount_polys) == 4 and
                    mount_centres == expected_centres and
                    board_mounts_good and
                    all(abs((poly.bounds[2] - poly.bounds[0]) -
                            PLATE_STANDOFF_DIAMETER) < 0.01
                        for poly in mount_polys) and
                    all(obstacle.distance(poly) >=
                        MOUNT_OPENING_CLEARANCE - 1e-6
                        for poly in mount_polys) and
                    all(obstacle.distance(Point(x, y).buffer(
                        STANDOFF_BODY_RADIUS)) >=
                        STANDOFF_OPENING_CLEARANCE - 1e-6
                        for x, y in expected_mounts) and
                    all(outline.exterior.distance(Point(x, y).buffer(
                        STANDOFF_BODY_RADIUS)) >=
                        STANDOFF_EDGE_CLEARANCE - 1e-6
                        for x, y in expected_mounts))
                all_voids = opening_polys + mount_polys
                material = outline.difference(unary_union(all_voids))
                one_piece = (material.geom_type == "Polygon" and
                             material.is_valid)
                side_checks = {
                    "dxf audit": not auditor.has_errors,
                    "valid outline": outline.is_valid,
                    "keycap bound": outside < 0.01,
                    "PCB profile": pcb_profile_error < 0.01,
                    "expected outline": outline.symmetric_difference(
                        expected_outline).area < 0.01,
                    "minimum web": minimum_web >= POM_MIN_WEB - 1e-6,
                    "four gasket mounts": len(integral_gasket_mounts) == 4,
                    "straight walls": straight_walls_good,
                    "contained openings": all(
                        outline.buffer(1e-6).contains(opening)
                        for opening in all_voids),
                    "mounts": mounts_good,
                    "no flex cuts": not obsolete_flex,
                    "one piece": one_piece,
                }
                good = all(side_checks.values())
                if not good:
                    failed = ", ".join(name for name, passed in side_checks.items()
                                       if not passed)
                    print(f"  {variant}/{side}: failed {failed}; "
                          f"web={minimum_web:.3f}, profile_error={pcb_profile_error:.4f}")
            except (OSError, ValueError, ezdxf.DXFError):
                good = False
            sides.append(good)
            ok &= good
        pair_symmetric = False
        if len(fabrication_outlines) == 2:
            mirrored_right = shapely_scale(
                fabrication_outlines[1], xfact=-1.0, yfact=1.0,
                origin=(axis_mm, 0.0))
            pair_symmetric = (
                fabrication_outlines[0].symmetric_difference(
                    mirrored_right).area < 0.01)
        if not pair_symmetric:
            sides = [False, False]
            ok = False
        gasket_good = False
        try:
            gasket_path = (ROOT / "plate" /
                           f"Symm60HE-gasket-pads-{variant}.dxf")
            gasket_doc = ezdxf.readfile(gasket_path)
            gasket_auditor = gasket_doc.audit()
            gasket_polys = [Polygon([
                (point[0], point[1])
                for point in entity.get_points("xy")
            ]) for entity in gasket_doc.modelspace().query(
                'LWPOLYLINE[layer=="GASKET_PADS"]')]
            gasket_good = (
                not gasket_auditor.has_errors and len(gasket_polys) == 8 and
                unary_union(gasket_polys).symmetric_difference(
                    unary_union(expected_gasket_pads)).area < 0.01)
        except (OSError, ValueError, ezdxf.DXFError):
            gasket_good = False
        ok &= gasket_good
        print(f"{variant}: left={'ok' if sides[0] else 'FAILED'}, "
              f"right={'ok' if sides[1] else 'FAILED'}, "
              f"gasket={'ok' if gasket_good else 'FAILED'}, "
              f"mirrored exterior={'ok' if pair_symmetric else 'FAILED'}; "
              "PCB-following profile, straight gasket walls, solid structure, "
              "integral gasket mounts, PCB-matched M2 mounts")
    print(">>> ok\n" if ok else ">>> FAILED\n")
    return ok


def case_geometry_audit():
    print("=== case/outline geometry ===")
    sys.path.insert(0, str(HERE))
    from outline import (LEFT_BLOCKER_FILL, RIGHT_BLOCKER_FILL,
                         LEFT_PLATE_BODY, RIGHT_PLATE_BODY,
                         LEFT_PCB_NOTCH_FILL, RIGHT_PCB_NOTCH_FILL,
                         LEFT_PCB, RIGHT_PCB, DB, PCB_EDGE_RADIUS,
                         LEFT_PLATE, RIGHT_PLATE,
                         LEFT_KEYCAP_ENVELOPE, RIGHT_KEYCAP_ENVELOPE)
    from mkcase import (left_outer, right_outer, left_cavity, right_cavity,
                        left_required, right_required, left_open, right_open,
                        left_fit_envelope, right_fit_envelope,
                        PLATE_CLEARANCE, PCB_CLEARANCE)
    from shapely.geometry import LineString
    from shapely.ops import polygonize
    scad = (ROOT / "case" / "Symm60HE-case.scad").read_text()
    fusion_step = ROOT / "case/fusion360/Symm60HE-case-Fusion360.step"
    fusion_source = ROOT / "case/fusion360/Symm60HE-case-Fusion360.FCStd"
    checks = {
        "left PCB keymap perimeter retained":
            LEFT_PCB.convex_hull.area - LEFT_PCB.area > 500.0,
        "right PCB keymap perimeter retained":
            RIGHT_PCB.convex_hull.area - RIGHT_PCB.area > 500.0,
        "left PCB selected notch filled":
            LEFT_PCB_NOTCH_FILL.buffer(-0.001).difference(LEFT_PCB).area < 1e-6,
        "right PCB selected notch filled":
            RIGHT_PCB_NOTCH_FILL.buffer(-0.001).difference(RIGHT_PCB).area < 1e-6,
        "PCB outside-edge radius is 1.0 mm": PCB_EDGE_RADIUS == 1.0,
        "left plate selected notch filled":
            LEFT_BLOCKER_FILL.difference(LEFT_PLATE_BODY).area < 1e-6,
        "right plate selected notch filled":
            RIGHT_BLOCKER_FILL.difference(RIGHT_PLATE_BODY).area < 1e-6,
        "clean left case exterior has four straight edges":
            len(left_outer.exterior.coords) - 1 == 4,
        "clean right case exterior has four straight edges":
            len(right_outer.exterior.coords) - 1 == 4,
        "smooth left bottom pocket has four straight edges":
            len(left_cavity.exterior.coords) - 1 == 4,
        "smooth right bottom pocket has four straight edges":
            len(right_cavity.exterior.coords) - 1 == 4,
        "smooth left pocket contains complete fit envelope":
            left_fit_envelope.difference(left_cavity).area < 1e-6,
        "smooth right pocket contains complete fit envelope":
            right_fit_envelope.difference(right_cavity).area < 1e-6,
        "left case retains full wall envelope":
            left_required.difference(left_outer).area < 1e-6,
        "right case retains full wall envelope":
            right_required.difference(right_outer).area < 1e-6,
        "left plate fits pocket with clearance":
            LEFT_PLATE.buffer(PLATE_CLEARANCE).difference(left_cavity).area < 1e-6,
        "right plate fits pocket with clearance":
            RIGHT_PLATE.buffer(PLATE_CLEARANCE).difference(right_cavity).area < 1e-6,
        "left PCB fits pocket with clearance":
            LEFT_PCB.buffer(PCB_CLEARANCE).difference(left_cavity).area < 1e-6,
        "right PCB fits pocket with clearance":
            RIGHT_PCB.buffer(PCB_CLEARANCE).difference(right_cavity).area < 1e-6,
        "left keycaps fit top opening":
            LEFT_KEYCAP_ENVELOPE.difference(left_open).area < 1e-6,
        "right keycaps fit top opening":
            RIGHT_KEYCAP_ENVELOPE.difference(right_open).area < 1e-6,
        "1.0 mm floor": bool(re.search(r"^floor_t\s*=\s*1\.000;", scad,
                                      re.MULTILINE)),
        "3.0 mm top overhang": bool(re.search(
            r"^top_overhang\s*=\s*3\.000;", scad, re.MULTILINE)),
        "connected top-frame overlap": bool(re.search(
            r"^top_join_drop\s*=\s*0\.750;", scad, re.MULTILINE)),
        "Fusion combined STEP present":
            fusion_step.is_file() and fusion_step.stat().st_size > 1_000_000,
        "Fusion FreeCAD source present":
            fusion_source.is_file() and fusion_source.stat().st_size > 100_000,
    }
    edge_pattern = re.compile(
        r"\(gr_line\s+\(start ([\d.-]+) ([\d.-]+)\)\s+"
        r"\(end ([\d.-]+) ([\d.-]+)\).*?\(layer \"Edge.Cuts\"\)",
        re.DOTALL)
    for name, expected in (("left", LEFT_PCB), ("right", RIGHT_PCB),
                           ("daughterboard", DB)):
        board = (ROOT / "pcb" / f"Symm60HE-{name.title()}.kicad_pcb").read_text()
        edges = [LineString([(float(x1), float(y1)), (float(x2), float(y2))])
                 for x1, y1, x2, y2 in edge_pattern.findall(board)]
        polygons = list(polygonize(edges))
        checks[f"{name} KiCad Edge.Cuts matches rounded source"] = (
            len(polygons) == 1 and
            polygons[0].symmetric_difference(expected).area < 0.01)
    for label, good in checks.items():
        print(f"{label}: {'ok' if good else 'FAILED'}")
    ok = all(checks.values())
    print(">>> ok\n" if ok else ">>> FAILED\n")
    return ok


def manufacturing_audit():
    """Verify the revised assembly-side, power-plane and panel contract."""
    print("=== manufacturing redesign ===")
    sys.path.insert(0, str(HERE))
    from sexp import loads, first, find
    from shapely.affinity import scale
    from outline import axis_mm
    from route import read
    checks = {}
    connector_centres = {}
    for side in ("Left", "Right"):
        board = loads((ROOT / "pcb" / f"Symm60HE-{side}.kicad_pcb").read_text())
        zones = {(first(z, "net")[1],
                  (first(z, "layer") or first(z, "layers"))[1])
                 for z in find(board, "zone")}
        checks[f"{side} has GND pours on both sides"] = {
            ("GND", "F.Cu"), ("GND", "B.Cu")}.issubset(zones)
        checks[f"{side} has no +3V3A plane"] = not any(
            net == "+3V3A" for net, _ in zones)
        connector_ref = "JL1" if side == "Left" else "JR1"
        connector = next(fp for fp in find(board, "footprint")
                         if next((p[2] for p in find(fp, "property")
                                  if len(p) > 2 and p[1] == "Reference"), "") ==
                         connector_ref)
        expected_angle = 270.0 if side == "Left" else 90.0
        checks[f"{connector_ref} has mirrored cable-entry orientation"] = (
            abs(float(first(connector, "at")[3]) % 360.0 - expected_angle) < 1e-6)
        connector_centres[side] = float(first(connector, "at")[1])
        half = side[0]
        physical_order = [
            "+3V3A", f"ADC_{half}5", "MUX_A0", "MUX_A1", "MUX_A2", "VBUS",
            f"ADC_{half}1", "GND", f"ADC_{half}2", f"RGB_{half}",
            f"ADC_{half}3", f"ADC_{half}4"]
        expected_pins = (list(reversed(physical_order))
                         if side == "Left" else physical_order)
        actual_pins = {}
        for pad in find(connector, "pad"):
            if str(pad[1]).isdigit():
                net = first(pad, "net")
                actual_pins[int(pad[1])] = (
                    net[2] if len(net) > 2 else net[1])
        checks[f"{connector_ref} pin mapping matches ribbon table"] = (
            [actual_pins.get(pin) for pin in range(1, 13)] == expected_pins)
    left_outline = read(str(ROOT / "pcb/Symm60HE-Left.kicad_pcb"))[2]
    right_outline = read(str(ROOT / "pcb/Symm60HE-Right.kicad_pcb"))[2]
    checks["half PCB edges are exact mirrors"] = (
        scale(left_outline, xfact=-1, yfact=1,
              origin=(axis_mm, 0)).symmetric_difference(right_outline).area <
        0.01)
    # The routed rear pockets intentionally place the connector references
    # 24 mm apart at these targets; their opposed rotations mirror cable entry.
    checks["half FFC locations match routed rear targets"] = (
        abs(connector_centres["Left"] - 140.209) < 1e-6 and
        abs(connector_centres["Right"] - 164.209) < 1e-6)
    panel = loads((ROOT / "pcb/Symm60HE-Panel.kicad_pcb").read_text())
    panel_smt = []
    mouse = 0
    panel_fiducials = 0
    tooling_holes = 0
    for fp in find(panel, "footprint"):
        attr = first(fp, "attr")
        layer = first(fp, "layer")[1]
        if fp[1] == "MouseBite_0.5mm":
            mouse += 1
        elif fp[1] == "Fiducial_1mm_BCu":
            panel_fiducials += 1
        elif fp[1] == "ToolingHole_2mm_NPTH":
            tooling_holes += 1
        if attr and "smd" in attr[1:]:
            panel_smt.append(layer)
    checks["panel SMT is one-sided on B.Cu"] = bool(panel_smt) and set(panel_smt) == {"B.Cu"}
    checks["panel has thirteen five-hole break rows"] = mouse == 65
    checks["panel has three global bottom-side fiducials"] = panel_fiducials == 3
    checks["panel has four 2 mm tooling holes"] = tooling_holes == 4
    edge_points = []
    for line in find(panel, "gr_line"):
        layer = first(line, "layer")
        if layer and layer[1] == "Edge.Cuts":
            for key in ("start", "end"):
                point = first(line, key)
                edge_points.append((float(point[1]), float(point[2])))
    px = [point[0] for point in edge_points]
    py = [point[1] for point in edge_points]
    checks["stacked panel is 162.29 x 227.83 mm"] = (
        abs((max(px) - min(px)) - 162.29) < 0.02 and
        abs((max(py) - min(py)) - 227.83) < 0.02)
    daughter = loads((ROOT / "pcb/Symm60HE-Daughterboard.kicad_pcb").read_text())
    _, _, daughter_outline, _ = read(
        str(ROOT / "pcb/Symm60HE-Daughterboard.kicad_pcb"))
    dx0, dy0, dx1, dy1 = daughter_outline.bounds
    checks["daughterboard outline is 50 x 31 mm"] = (
        abs((dx1 - dx0) - 50.0) < 0.01 and
        abs((dy1 - dy0) - 31.0) < 0.01)
    daughter_zones = {(first(z, "net")[1],
                       (first(z, "layer") or first(z, "layers"))[1])
                      for z in find(daughter, "zone")}
    checks["daughterboard has GND pours on both sides"] = {
        ("GND", "F.Cu"), ("GND", "B.Cu")}.issubset(daughter_zones)
    checks["daughterboard has no +3V3A plane"] = not any(
        net == "+3V3A" for net, _ in daughter_zones)
    daughter_sides = {first(fp, "layer")[1] for fp in find(daughter, "footprint")
                      if first(fp, "attr") and "smd" in first(fp, "attr")[1:]}
    checks["compact daughterboard remains mixed-side"] = daughter_sides == {"F.Cu", "B.Cu"}
    daughter_fids = {"F.Cu": 0, "B.Cu": 0}
    daughter_mounts = {}
    for fp in find(daughter, "footprint"):
        if "Fiducial_1mm_" in str(fp[1]):
            daughter_fids[first(fp, "layer")[1]] += 1
        reference = next((str(prop[2]) for prop in find(fp, "property")
                          if len(prop) > 2 and
                          str(prop[1]) == "Reference"), "")
        if reference.startswith("MHD"):
            position = first(fp, "at")
            daughter_mounts[reference] = (
                float(position[1]), float(position[2]))
    checks["daughterboard has no local fiducial footprints"] = (
        daughter_fids == {"F.Cu": 0, "B.Cu": 0})
    expected_mounts = {
        "MHD1": (165.209, -3.5000),
        "MHD3": (209.209, -3.5000),
        "MHD4": (165.209, 20.9734),
        "MHD2": (209.209, 20.9734),
    }
    checks["daughterboard has four symmetric perimeter case mounts"] = (
        daughter_mounts.keys() == expected_mounts.keys() and
        all(math.dist(daughter_mounts[ref], target) < 0.002
            for ref, target in expected_mounts.items()))

    ffc_count = 0
    for name in BOARDS:
        board = loads((ROOT / "pcb" / f"{name}.kicad_pcb").read_text())
        for fp in find(board, "footprint"):
            if "FFC_12P_1.00mm_TopContact" not in str(fp[1]):
                continue
            ffc_count += 1
            signal = [pad for pad in find(fp, "pad")
                      if str(pad[1]).isdigit()]
            mounts = [pad for pad in find(fp, "pad") if str(pad[1]) == "MP"]
            checks[f"{name} {next(p[2] for p in find(fp, 'property') if p[1] == 'Reference')} exact C20111 lands"] = (
                len(signal) == 12 and len(mounts) == 2 and
                all([float(x) for x in first(pad, "size")[1:3]] == [0.6, 2.2]
                    and abs(abs(float(first(pad, "at")[2])) - 1.1) < 1e-6
                    for pad in signal) and
                all([float(x) for x in first(pad, "size")[1:3]] == [1.8, 2.6]
                    and abs(abs(float(first(pad, "at")[1])) - 7.8) < 1e-6
                    and abs(abs(float(first(pad, "at")[2])) - 1.1) < 1e-6
                    for pad in mounts))
    checks["four FFC connectors use the locked footprint"] = ffc_count == 4
    for label, good in checks.items():
        print(f"{label}: {'ok' if good else 'FAILED'}")
    ok = all(checks.values())
    print(">>> ok\n" if ok else ">>> FAILED\n")
    return ok


def reference_assembly_audit():
    print("=== Fusion reference assembly ===")
    fusion = ROOT / "case/fusion360"
    old_case = [ROOT / "case/Symm60HE-case.scad",
                ROOT / "case/Symm60HE-case-top.stl",
                ROOT / "case/Symm60HE-case-bottom.stl"]
    def large_enough(path, size):
        return path.is_file() and path.stat().st_size > size

    checks = {
        "old case solids and OpenSCAD source removed": not any(p.exists() for p in old_case),
        "Fusion reference STEP present":
            large_enough(fusion / "Symm60HE-reference-assembly.step", 100_000),
        "editable FreeCAD source present":
            large_enough(fusion / "Symm60HE-reference-assembly.FCStd", 10_000),
        "Fusion handoff instructions present": (fusion / "README.md").is_file(),
    }
    for name in ("LeftPCB", "RightPCB", "DaughterboardPCB", "LeftPlate",
                 "RightPlate", "LeftSwitches", "RightSwitches",
                 "LeftKeycaps", "RightKeycaps"):
        path = fusion / f"Symm60HE-{name}.step"
        checks[f"separate {name} body"] = path.is_file() and path.stat().st_size > 1_000
    for label, good in checks.items():
        print(f"{label}: {'ok' if good else 'FAILED'}")
    ok = all(checks.values())
    print(">>> ok\n" if ok else ">>> FAILED\n")
    return ok


def main():
    checks = [
        two_layer_audit(),
        run_project_check("pad conflicts", "_check_pads.py"),
        run_project_check("nets", "netcheck.py"),
        run_project_check("schematic/PCB parity", "schematic_parity.py"),
        kicad_drc(),
        run_project_check("ignored DRC rules", "audit_ignored.py"),
        kicad_erc(),
        firmware_check(),
        release_check(),
        split_plate_audit(),
        manufacturing_audit(),
        reference_assembly_audit(),
    ]
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
