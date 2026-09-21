#!/usr/bin/env python3
"""Build a PCBWay-specific fabrication and assembly package for Neo pogo boards."""
from collections import defaultdict
from pathlib import Path
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "pcb/variants/pogo-neo"
PANELS = SOURCE / "panels"
OUT = ROOT / "release/pcbway-pogo-neo"
ARCHIVE = ROOT / "release/Symm60HE-PCBWay-Pogo-Neo.zip"
LAYERS = "F.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,Edge.Cuts"

sys.path.insert(0, str(ROOT / "tools"))
from release_neo_pogo import (HALF_BOARDS, LAYOUTS, PARTS,  # noqa: E402
                              export_positions, find_cli, fitted_footprints,
                              selected_half_refs, sort_refs)

COMMON = {
    "Controller": SOURCE / "Symm60HE-Neo-Controller.kicad_pcb",
    "Left-SpringModule": SOURCE / "Symm60HE-Neo-Left-SpringModule.kicad_pcb",
    "Right-SpringModule": SOURCE / "Symm60HE-Neo-Right-SpringModule.kicad_pcb",
}
HALVES = {
    "Left": SOURCE / "Symm60HE-Neo-Left-Half.kicad_pcb",
    "Right": SOURCE / "Symm60HE-Neo-Right-Half.kicad_pcb",
}
FAMILY_PANELS = {
    "Hall-Family": PANELS / "Symm60HE-Neo-Hall-Family-Panel.kicad_pcb",
    "Centre-Family": PANELS / "Symm60HE-Neo-Centre-Family-Panel.kicad_pcb",
}

DESCRIPTIONS = {
    "854-22-012-30-004101": "12-position 1.27 mm SMT spring-loaded connector",
    "856-10-012-30-051000": "12-position 1.27 mm SMT mating target connector",
    "FFC_12P_1.00mm": "12-position 1.00 mm top-contact FFC connector",
    "MT9102ET": "Hall-effect keyboard sensor",
    "SN74LV4051A": "8-channel analog multiplexer",
    "AT32F405RCT7": "ARM microcontroller",
    "TYPE-C-31-M-12": "USB Type-C receptacle",
}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def instructions(value):
    if value == "854-22-012-30-004101":
        return ("NO SUBSTITUTE; mechanically critical; manual SMT placement "
                "acceptable; spring contacts face Hall-PCB target")
    if value == "856-10-012-30-051000":
        return ("NO SUBSTITUTE; mechanically critical; target face points "
                "toward floating spring module")
    if value == "MT9102ET":
        return "Alignment-sensitive Hall sensor; no substitution without written approval"
    if value.startswith("FFC_12P"):
        return "Top-contact orientation; verify cable-entry direction in assembly drawing"
    if value == "TYPE-C-31-M-12":
        return "Verify shell stakes, pin 1, and connector mouth direction"
    return "Substitution only with written approval"


def write_bom(path, footprints, selected):
    grouped = defaultdict(list)
    for reference in selected:
        part = footprints[reference]
        value = part["value"]
        if value not in PARTS:
            raise RuntimeError(f"No sourcing record for {value} ({reference})")
        manufacturer, mpn, distributor_part, method = PARTS[value]
        grouped[(value, part["footprint"], manufacturer, mpn,
                 distributor_part, method)].append(reference)
    headers = ["Item", "Quantity", "Reference Designators", "Description",
               "Package", "Assembly Type", "Manufacturer",
               "Manufacturer Part Number", "Distributor",
               "Distributor Part Number", "Substitution Allowed",
               "Special Instructions"]
    with path.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(headers)
        for item, (key, refs) in enumerate(sorted(grouped.items()), 1):
            value, footprint, manufacturer, mpn, distributor_part, _ = key
            pogo = value in {"854-22-012-30-004101", "856-10-012-30-051000"}
            distributor = "PCBWay turnkey quote or customer consigned" if pogo else "LCSC"
            writer.writerow([
                item, len(refs), ",".join(sort_refs(refs)),
                DESCRIPTIONS.get(value, value), footprint, "SMT", manufacturer,
                mpn, distributor, distributor_part, "No" if pogo else "Written approval only",
                instructions(value),
            ])


def write_centroid(path, rows, selected, footprints):
    found = set()
    with path.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Designator", "Mid X (mm)", "Mid Y (mm)", "Layer",
                         "Rotation (deg)", "Value", "Package"])
        for row in sorted(rows, key=lambda item: sort_refs([item["Ref"]])[0]):
            reference = row["Ref"]
            if reference not in selected:
                continue
            part = footprints[reference]
            writer.writerow([
                reference, row["PosX"], row["PosY"],
                "Top" if row["Side"] == "top" else "Bottom", row["Rot"],
                part["value"], part["footprint"],
            ])
            found.add(reference)
    if found != set(selected):
        raise RuntimeError(f"{path}: centroid mismatch: missing={sorted(set(selected)-found)}")
    return len(found)


def export_pdf(cli, board, output, layers, mirror=False):
    command = [cli, "pcb", "export", "pdf", "--mode-single", "--black-and-white",
               "--sketch-pads-on-fab-layers", "--drill-shape-opt", "2",
               "--check-zones", "--layers", layers, "-o", str(output)]
    if mirror:
        command.append("--mirror")
    command.append(str(board))
    subprocess.run(command, check=True, capture_output=True, text=True)


def export_fabrication(cli, board, output, source_label):
    fabrication = output / "fabrication"
    gerbers = fabrication / "gerbers"
    drawings = output / "drawings"
    sources = output / "source"
    gerbers.mkdir(parents=True, exist_ok=True)
    drawings.mkdir(parents=True, exist_ok=True)
    sources.mkdir(parents=True, exist_ok=True)

    drc = fabrication / f"{source_label}-DRC.rpt"
    result = subprocess.run([
        cli, "pcb", "drc", "--refill-zones", "--severity-all",
        "--exit-code-violations", "-o", str(drc), str(board),
    ], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"{board.name} DRC failed:\n{result.stdout}\n{result.stderr}")
    report = drc.read_text()
    if "** Found 0 DRC violations **" not in report or "** Found 0 unconnected pads **" not in report:
        raise RuntimeError(f"{board.name}: DRC report is not clean")

    subprocess.run([
        cli, "pcb", "export", "gerbers", "--layers", LAYERS,
        "--subtract-soldermask", "--check-zones", "--precision", "6",
        "-o", str(gerbers), str(board),
    ], check=True, capture_output=True, text=True)
    subprocess.run([
        cli, "pcb", "export", "drill", "--format", "excellon",
        "--excellon-units", "mm", "--excellon-separate-th",
        "--generate-report", "--report-path", str(fabrication / "drill-report.txt"),
        "-o", str(gerbers), str(board),
    ], check=True, capture_output=True, text=True)
    export_pdf(cli, board, drawings / "Top-Assembly.pdf",
               "F.Fab,F.Silkscreen,Edge.Cuts")
    export_pdf(cli, board, drawings / "Bottom-Assembly-Mirrored.pdf",
               "B.Fab,B.Silkscreen,Edge.Cuts", mirror=True)
    export_pdf(cli, board, drawings / "Fabrication-Outline-and-Drills.pdf",
               "Edge.Cuts")

    shutil.copy2(board, sources / board.name)
    project = board.with_suffix(".kicad_pro")
    if project.exists():
        shutil.copy2(project, sources / project.name)
    fp_table = board.parent / "fp-lib-table"
    if fp_table.exists():
        shutil.copy2(fp_table, sources / "fp-lib-table")

    archive = fabrication / f"{source_label}-Gerbers-and-Drills.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
        for path in sorted(gerbers.iterdir()):
            zipped.write(path, path.name)
    with zipfile.ZipFile(archive) as zipped:
        if zipped.testzip():
            raise RuntimeError(f"Corrupt fabrication archive: {archive}")
    return archive


def assembly_files(cli, board, output, selected):
    footprints = fitted_footprints(board)
    missing = set(selected) - set(footprints)
    if missing:
        raise RuntimeError(f"{board.name}: selected footprints missing: {sorted(missing)}")
    output.mkdir(parents=True, exist_ok=True)
    raw = output / ".positions.csv"
    rows = export_positions(cli, board, raw)
    if raw.exists():
        raw.unlink()
    bom = output / "PCBWay-BOM.csv"
    centroid = output / "PCBWay-Centroid.csv"
    write_bom(bom, footprints, selected)
    count = write_centroid(centroid, rows, selected, footprints)
    return count


def panel_hall_refs(layout):
    return ({f"LH-{ref}" for ref in selected_half_refs("Left", layout)} |
            {f"RH-{ref}" for ref in selected_half_refs("Right", layout)})


def write_support_files():
    (OUT / "PCBWay-RFQ-Notes.txt").write_text(
        "Symm60HE Neo direct-target pogo PCBA quotation\n\n"
        "Quote two independent family-panel assemblies:\n"
        "1. Hall-Family: two different designs, bottom-side SMT assembly.\n"
        "2. Centre-Family: three different designs, both-side SMT assembly.\n\n"
        "Fabrication: 2 layers, 1.2 mm finished FR-4, 1 oz copper, IPC Class 2, "
        "100% electrical test. ENIG is recommended for the prototype quotation.\n"
        "Do not alter panel outlines, tab routes, tooling holes, or fiducials without approval.\n\n"
        "NO SUBSTITUTION:\n"
        "Mill-Max 854-22-012-30-004101 spring connector, PS1 on both spring modules.\n"
        "Mill-Max 856-10-012-30-051000 target, PTL1/PTR1 on Hall PCBs.\n"
        "Manual SMT placement is acceptable. Confirm turnkey sourcing, packaging, "
        "soldering process, side, and rotation before order acceptance.\n"
        "The mating interface is mechanically critical; inspect all 12 contacts.\n")
    with (OUT / "PCBWay-Fabrication-Specification.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Parameter", "Requested value", "Notes"])
        writer.writerows([
            ["Layers", "2", "F.Cu and B.Cu"],
            ["Finished thickness", "1.2 mm", "Required for mechanical stack"],
            ["Material", "FR-4", "Standard Tg acceptable for prototype"],
            ["Copper", "1 oz outer", "No controlled impedance requirement"],
            ["Surface finish", "ENIG recommended", "Confirm quotation before production"],
            ["Solder mask", "Customer selection", "Green acceptable"],
            ["Silkscreen", "White", "Use supplied plots"],
            ["Electrical test", "100%", "All fabricated boards"],
            ["Quality", "IPC Class 2", "Prototype/consumer keyboard"],
            ["Panel delivery", "Depanel after assembly only if quoted", "Protect irregular edges"],
        ])
    with (OUT / "Critical-Connector-Placements.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Panel", "Designator", "Manufacturer", "MPN", "Side",
                         "Rotation", "Substitution", "Inspection"])
        writer.writerows([
            ["Centre-Family", "LS-PS1", "Mill-Max", "854-22-012-30-004101",
             "Top", "180", "Prohibited", "Spring faces target; all 12 contacts coplanar"],
            ["Centre-Family", "RS-PS1", "Mill-Max", "854-22-012-30-004101",
             "Top", "0", "Prohibited", "Spring faces target; all 12 contacts coplanar"],
            ["Hall-Family", "LH-PTL1", "Mill-Max", "856-10-012-30-051000",
             "Bottom", "-90", "Prohibited", "Target face clean and parallel"],
            ["Hall-Family", "RH-PTR1", "Mill-Max", "856-10-012-30-051000",
             "Bottom", "90", "Prohibited", "Target face clean and parallel"],
        ])


def main():
    cli = find_cli()
    subprocess.run([sys.executable, str(ROOT / "tools/pogo/panelize_neo_pogo.py")], check=True)
    subprocess.run([sys.executable, str(ROOT / "tools/pogo/verify_neo_pogo.py")], check=True)
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    write_support_files()
    manifest = {
        "release": "PCBWay Neo direct-target pogo",
        "pcb_count": 5,
        "family_panels": {},
        "individual_boards": {},
        "layouts": list(LAYOUTS),
        "pogo_policy": "exact MPN only; PCBWay turnkey quote or customer consignment",
    }

    for name, board in COMMON.items():
        target = OUT / "individual-boards" / name
        archive = export_fabrication(cli, board, target, name)
        selected = set(fitted_footprints(board))
        count = assembly_files(cli, board, target / "assembly", selected)
        manifest["individual_boards"][name] = {
            "placements": count, "fabrication_zip": archive.name,
            "source_sha256": sha256(board),
        }

    for side, board in HALVES.items():
        target = OUT / "individual-boards" / f"{side}-Half"
        archive = export_fabrication(cli, board, target, f"{side}-Half")
        layout_counts = {}
        for layout in LAYOUTS:
            selected = selected_half_refs(side, layout)
            layout_counts[layout] = assembly_files(
                cli, board, target / "assembly" / "layouts" / layout, selected)
        manifest["individual_boards"][f"{side}-Half"] = {
            "placements_by_layout": layout_counts,
            "fabrication_zip": archive.name, "source_sha256": sha256(board),
        }

    hall = FAMILY_PANELS["Hall-Family"]
    hall_target = OUT / "family-panels/Hall-Family"
    hall_archive = export_fabrication(cli, hall, hall_target, "Hall-Family-Panel")
    hall_counts = {}
    for layout in LAYOUTS:
        hall_counts[layout] = assembly_files(
            cli, hall, hall_target / "assembly/layouts" / layout,
            panel_hall_refs(layout))
    manifest["family_panels"]["Hall-Family"] = {
        "different_designs": 2, "assembly_sides": "Bottom",
        "placements_by_layout": hall_counts,
        "fabrication_zip": hall_archive.name, "source_sha256": sha256(hall),
    }

    centre = FAMILY_PANELS["Centre-Family"]
    centre_target = OUT / "family-panels/Centre-Family"
    centre_archive = export_fabrication(cli, centre, centre_target,
                                        "Centre-Family-Panel")
    centre_selected = set(fitted_footprints(centre))
    centre_count = assembly_files(cli, centre, centre_target / "assembly",
                                  centre_selected)
    manifest["family_panels"]["Centre-Family"] = {
        "different_designs": 3, "assembly_sides": "Both",
        "placements": centre_count, "fabrication_zip": centre_archive.name,
        "source_sha256": sha256(centre),
    }

    readme = OUT / "README.md"
    readme.write_text(
        "# Symm60HE PCBWay Neo-pogo manufacturing package\n\n"
        "This release is independent of `release/jlcpcb-pogo-neo`. It contains "
        "production plots, drills, assembly PDFs, PCBWay BOMs and centroids for "
        "the five active 1.2 mm, two-layer boards and two customer-designed family "
        "panels.\n\n"
        "## Recommended order\n\n"
        "Order `family-panels/Hall-Family/fabrication/Hall-Family-Panel-Gerbers-and-Drills.zip` "
        "as a two-design panel with bottom-side assembly. Choose exactly one matching "
        "BOM/centroid pair under `assembly/layouts/`. Order "
        "`family-panels/Centre-Family/fabrication/Centre-Family-Panel-Gerbers-and-Drills.zip` "
        "as a three-design panel with both-side assembly. Do not combine a BOM from "
        "one layout with a centroid from another.\n\n"
        "The `individual-boards/` tree is supplied for review, rework, and alternate "
        "quoting. Do not order an individual-board Gerber ZIP and its containing family "
        "panel for the same required quantity.\n\n"
        "The Mill-Max 854 spring and 856 target placements are included by exact MPN. "
        "No substitute is authorized. PCBWay must confirm turnkey sourcing or customer "
        "consignment and manual-placement capability before production. See "
        "`PCBWay-RFQ-Notes.txt` and `Critical-Connector-Placements.csv`.\n\n"
        "The assembly PDFs show physical reference geometry for both sides. The matched "
        "layout BOM and centroid are authoritative for which universal-layout Hall "
        "positions are fitted. Confirm every side and rotation in PCBWay's engineering "
        "review before payment.\n")
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    checksummed = sorted(path for path in OUT.rglob("*")
                         if path.is_file() and path.name != "SHA256SUMS.txt")
    (OUT / "SHA256SUMS.txt").write_text("".join(
        f"{sha256(path)}  {path.relative_to(OUT)}\n" for path in checksummed))
    with zipfile.ZipFile(ARCHIVE, "w", zipfile.ZIP_DEFLATED) as zipped:
        for path in sorted(item for item in OUT.rglob("*") if item.is_file()):
            zipped.write(path, OUT.name / path.relative_to(OUT))
    with zipfile.ZipFile(ARCHIVE) as zipped:
        if zipped.testzip():
            raise RuntimeError("PCBWay release ZIP failed integrity test")
    (ARCHIVE.with_suffix(ARCHIVE.suffix + ".sha256")).write_text(
        f"{sha256(ARCHIVE)}  {ARCHIVE.name}\n")
    print(OUT.relative_to(ROOT))
    print(ARCHIVE.relative_to(ROOT), sha256(ARCHIVE))
    print(json.dumps(manifest["family_panels"], indent=2))


if __name__ == "__main__":
    main()
