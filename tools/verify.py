#!/usr/bin/env python3
"""Run the release checks against the current two-layer boards.

KiCad is authoritative for curved outlines, filled zones, copper clearance and
connectivity. The project-specific scripts independently check overlapping
multi-layout pads and the Hall-sensor/mux/ribbon net architecture.
"""
import glob
import csv
import json
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
PLATE_VARIANTS = ("wkl", "wklbs2", "wklarrows", "wklbs2arrows", "universal")
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
            # KiCad stores the intentionally mirrored, rotated B.Cu FFC copies
            # in a transformed representation.  Their copper/pad dimensions are
            # checked independently below; permit only that exact library-copy
            # comparison warning, never electrical or geometry violations.
            only_known_back_ffc_warning = (
                name in {"Symm60HE-Left", "Symm60HE-Right", "Symm60HE-Panel"}
                and violations
                and set(violations) == {"lib_footprint_mismatch"}
                and report_text.count("FFC_12P_1.00mm_TopContact") == len(violations))
            ok &= result.returncode == 0 or only_known_back_ffc_warning
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
        good = (data["keyboard"]["num_keys"] == 63 and
                data["analog"]["mux"]["select"] == ["C1", "C2", "C3"] and
                data["analog"]["mux"]["input"] ==
                ["A3", "A4", "A5", "A6", "A7", "C4", "C5", "B0"] and
                mapped == list(range(1, 64)) and image.is_file() and
                image.stat().st_size > 0)
        print(f"63 channels once each; firmware.bin={image.stat().st_size if image.exists() else 0} bytes")
    except (KeyError, OSError, ValueError, TypeError) as exc:
        print(exc)
        good = False
    print(">>> ok\n" if good else ">>> FAILED\n")
    return good


def release_check():
    print("=== fabrication archives ===")
    ok = True
    import zipfile
    for name in ("Symm60HE-Half-Panel", "Symm60HE-Daughterboard"):
        archive = ROOT / "release/jlcpcb" / f"{name}-Gerbers.zip"
        try:
            with zipfile.ZipFile(archive) as zipped:
                names = zipped.namelist()
                archive_good = zipped.testzip() is None and len(names) >= 9
            if name == "Symm60HE-Half-Panel":
                bom_rows = []
                pairs_good = True
                for layout in ("doe-wkl", "doe-wklarrows", "doe-wklbs2",
                               "doe-wklbs2arrows"):
                    base = ROOT / "release/jlcpcb" / name / "layouts" / layout
                    bom = base / f"{name}-{layout}-BOM.csv"
                    cpl = base / f"{name}-{layout}-CPL.csv"
                    rows = list(csv.DictReader(bom.open()))
                    positions = list(csv.DictReader(cpl.open()))
                    bom_refs = {ref for row in rows
                                for ref in row["Designator"].split(",")}
                    cpl_refs = {row["Ref"] for row in positions}
                    pairs_good &= (bool(rows) and bom_refs == cpl_refs and
                                   all(row["LCSC Part #"] not in ("", "--")
                                       for row in rows))
                    bom_rows.extend(rows)
                good = archive_good and pairs_good
            else:
                bom = ROOT / "release/jlcpcb" / name / f"{name}-BOM.csv"
                bom_rows = list(csv.DictReader(bom.open()))
                good = (archive_good and bool(bom_rows) and
                        all(row["LCSC Part #"] not in ("", "--")
                            for row in bom_rows))
        except (OSError, zipfile.BadZipFile):
            good = False
            names = []
            bom_rows = []
        print(f"{name}: {len(names)} files, {len(bom_rows)} fitted SMT BOM rows" +
              ("" if good else "  FAILED"))
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
    ok = True
    for variant in PLATE_VARIANTS:
        sides = []
        for side in ("left", "right"):
            path = ROOT / "plate" / f"Symm60HE-plate-{variant}-{side}.dxf"
            try:
                doc = ezdxf.readfile(path)
                auditor = doc.audit()
                outlines = list(doc.modelspace().query(
                    'LWPOLYLINE[layer=="PLATE_OUTLINE"]'))
                good = not auditor.has_errors and len(outlines) == 1
            except (OSError, ezdxf.DXFError):
                good = False
            sides.append(good)
            ok &= good
        print(f"{variant}: left={'ok' if sides[0] else 'FAILED'}, "
              f"right={'ok' if sides[1] else 'FAILED'}")
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
            "+3V3A", "GND", "MUX_A0", "MUX_A1", "MUX_A2", "GND",
            f"ADC_{half}1", "GND", f"ADC_{half}2", "GND",
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
    checks["half FPC connector locations are symmetric"] = abs(
        connector_centres["Left"] + connector_centres["Right"] -
        2 * axis_mm) < 1e-6
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
    checks["stacked panel is 175.32 x 233.91 mm"] = (
        abs((max(px) - min(px)) - 175.32) < 0.02 and
        abs((max(py) - min(py)) - 233.91) < 0.02)
    daughter = loads((ROOT / "pcb/Symm60HE-Daughterboard.kicad_pcb").read_text())
    _, _, daughter_outline, _ = read(
        str(ROOT / "pcb/Symm60HE-Daughterboard.kicad_pcb"))
    dx0, dy0, dx1, dy1 = daughter_outline.bounds
    checks["daughterboard outline is 57 x 27 mm"] = (
        abs((dx1 - dx0) - 57.0) < 0.01 and
        abs((dy1 - dy0) - 27.0) < 0.01)
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
    for fp in find(daughter, "footprint"):
        if "Fiducial_1mm_" in str(fp[1]):
            daughter_fids[first(fp, "layer")[1]] += 1
    checks["daughterboard has three fiducials per assembly side"] = (
        daughter_fids == {"F.Cu": 3, "B.Cu": 3})

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
    checks["four FPC-compatible ZIF connectors use the locked footprint"] = ffc_count == 4
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
                 "LeftKeycaps", "RightKeycaps", "LeftPCBComponents",
                 "RightPCBComponents", "DaughterboardComponents"):
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
        run_project_check("3D model provenance", "verify_model_provenance.py"),
        reference_assembly_audit(),
    ]
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
