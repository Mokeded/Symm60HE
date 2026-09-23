#!/usr/bin/env python3
"""Create deterministic JLCPCB fabrication/placement release artifacts."""
from collections import defaultdict
from pathlib import Path
import csv
import hashlib
import shutil
import subprocess
import zipfile

from generators.mkschematics import components
from sexp import find, first, loads
from verify import ROOT, find_kicad_cli

LAYERS = "F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def bom_lookup():
    rows = []
    with (ROOT / "Symm60HE-BOM.csv").open() as stream:
        for row in csv.reader(stream):
            if row and row[0].isdigit():
                rows.append(row)
    result = {}
    for row in rows:
        # All table forms place value in column 1, MPN in column 4 and LCSC in
        # the penultimate column. Index both human values and exact MPNs.
        result.setdefault(row[1], row[-2])
        if len(row) > 4 and row[4] not in ("", "--"):
            result.setdefault(row[4], row[-2])
    aliases = {
        "0.5A": "BSMD0805-050-24V",
        "12MHz": "X322512MSB4SI",
        "FFC_12P": "1.0-12P",
        "TS-1187A": "TS-1187A-B-A-B",
        "XC6206P332MR": "XC6206P332MR-G",
    }
    for board_value, bom_value in aliases.items():
        if bom_value in result:
            result[board_value] = result[bom_value]
    return result


def write_board_bom(name, output, selected=None, board_path=None):
    grouped = defaultdict(list)
    descriptions = {}
    board_path = board_path or ROOT / "pcb" / f"{name}.kicad_pcb"
    board = loads(board_path.read_text())
    smt_refs = set()
    dnp_refs = set()
    for fp in find(board, "footprint"):
        attr = first(fp, "attr")
        if not attr or "smd" not in attr[1:] or "board_only" in attr[1:]:
            continue
        reference = next((p[2] for p in find(fp, "property")
                          if len(p) > 2 and p[1] == "Reference"), "")
        if reference:
            smt_refs.add(str(reference))
            if "dnp" in {str(value) for value in attr[1:]}:
                dnp_refs.add(str(reference))
    for part in components(board_path):
        if part["ref"] not in smt_refs or part["ref"] in dnp_refs or (selected is not None and
                                            part["ref"] not in selected):
            continue
        grouped[(part["value"], part["footprint"])].append(part["ref"])
        descriptions[part["value"]] = part["value"]
    lcsc = bom_lookup()
    with output.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (value, footprint), refs in sorted(grouped.items()):
            writer.writerow([value, ",".join(refs), footprint.split(":")[-1],
                             lcsc.get(value, "--")])


def panel_layout_refs(layout):
    """Return the exact prefixed panel references fitted for one layout."""
    short_layout = layout.removeprefix("doe-")
    with (ROOT / "Symm60HE-sensor-aliases.csv").open(newline="") as stream:
        aliases = {row["switch_ref"]: row["sensor_ref"]
                   for row in csv.DictReader(stream)}
    selected = set()
    with (ROOT / "Symm60HE-switch-map.csv").open(newline="") as stream:
        for row in csv.DictReader(stream):
            if short_layout not in row["in_builds"].split():
                continue
            side = row["half"]
            index = int(row["ref"][3:])
            sensor_prefix = "HEL" if side == "L" else "HER"
            cap_prefix = "CL" if side == "L" else "CR"
            sensor = aliases.get(row["ref"], f"{sensor_prefix}{index}")
            sensor_index = int(sensor[3:])
            selected.update((f"{side}-{sensor}",
                             f"{side}-{cap_prefix}{sensor_index}A",
                             f"{side}-{cap_prefix}{sensor_index}B"))
    for side, mux, cap, connector in (
            ("L", "AML", "CML", "JL1"),
            ("R", "AMR", "CMR", "JR1")):
        selected.update(f"{side}-{mux}{index}" for index in range(1, 5))
        selected.update(f"{side}-{cap}{index}" for index in range(1, 5))
        selected.add(f"{side}-{connector}")
    return selected


def filter_cpl(source, output, selected):
    with source.open(newline="") as stream:
        reader = csv.DictReader(stream)
        fieldnames = reader.fieldnames
        rows = [row for row in reader if row["Ref"] in selected]
    found = {row["Ref"] for row in rows}
    missing = selected - found
    if missing:
        raise RuntimeError(f"CPL is missing selected references: {sorted(missing)}")
    with output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main():
    cli = find_kicad_cli()
    if not cli:
        raise SystemExit("kicad-cli not found")
    release = ROOT / "release/jlcpcb"
    if release.exists():
        shutil.rmtree(release)
    release.mkdir(parents=True)
    archives = []
    targets = (("Symm60HE-Half-Panel", "Symm60HE-Panel"),
               ("Symm60HE-Daughterboard", "Symm60HE-Daughterboard"))
    for name, board_name in targets:
        board = ROOT / "pcb" / f"{board_name}.kicad_pcb"
        board_dir = release / name
        gerber_dir = board_dir / "gerbers"
        gerber_dir.mkdir(parents=True)
        subprocess.run([cli, "pcb", "export", "gerbers", "--layers", LAYERS,
                        "--subtract-soldermask", "--check-zones", "-o", str(gerber_dir),
                        str(board)], check=True)
        subprocess.run([cli, "pcb", "export", "drill", "--format", "excellon",
                        "--excellon-units", "mm", "--excellon-separate-th",
                        "--generate-report", "--report-path", str(board_dir / "drill-report.txt"),
                        "-o", str(gerber_dir), str(board)], check=True)
        raw_cpl = board_dir / f"{name}-all-fitted-CPL.csv"
        subprocess.run([cli, "pcb", "export", "pos", "--format", "csv", "--units", "mm",
                        "--side", "both", "--exclude-dnp", "-o",
                        str(raw_cpl), str(board)], check=True)
        raw_cpl.rename(board_dir / f"{name}-CPL.csv")
        write_board_bom(board_name, board_dir / f"{name}-BOM.csv")
        archive = release / f"{name}-Gerbers.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
            for path in sorted(gerber_dir.iterdir()):
                zipped.write(path, path.name)
        archives.append(archive)
    readme = release / "README.md"
    readme.write_text(
        "# Symm60HE JLCPCB release\n\n"
        "The two keyboard halves are connected in `Symm60HE-Half-Panel-Gerbers.zip` "
        "as a 162.29 x 227.83 mm stacked panel with routed rails, thirteen "
        "5-hole mouse-bite rows at 0.75 mm pitch, three global B.Cu fiducials, four "
        "2 mm tooling holes and all SMT components on B.Cu. Order that ZIP as one "
        "assembled PCB. Order the 50 x 31 mm compact mixed-side daughterboard "
        "separately with "
        "`Symm60HE-Daughterboard-Gerbers.zip`; it retains only its four symmetric "
        "M2 NPTH case mounts and has no local fiducial footprints. Both designs are "
        "2-layer, 1.2 mm finished thickness. The "
        "generated BOMs contain every fitted universal-layout Hall sensor, all ten "
        "muxes and the reverse-mount RGB LEDs. Every line has an exact LCSC "
        "assignment. Use the single matched BOM/CPL pair: every assembled board "
        "supports all four physical layouts, while firmware profiles mask the "
        "inactive Hall channels.\n\n"
        "Gerbers include both copper layers, both solder masks, both silkscreens and "
        "Edge.Cuts. Silkscreen was clipped to solder-mask openings during plotting.\n\n"
        "The panel's right board uses four explicit 1.75 mm-wide routed NPTH slots "
        "where mutually exclusive universal-layout alignment holes overlap. Confirm all "
        "four unplated slots in the fabricator viewer before payment.\n")
    checklist = release / "ORDER-CHECKLIST.md"
    checklist.write_text(
        "# Symm60HE prototype-order checklist\n\n"
        "Use these settings for both PCB orders unless the fabricator flags a "
        "specific incompatibility:\n\n"
        "- 2 copper layers\n"
        "- 1.2 mm finished FR-4 thickness\n"
        "- 1 oz finished copper\n"
        "- black solder mask and white silkscreen\n"
        "- electrical test enabled\n"
        "- via covering: tented (solder mask over vias). A few GND pads on the "
        "half boards carry a 0.6/0.3 mm via inside the pad where the south-side "
        "LED pocket left no other stitch path; tenting keeps those pads "
        "solderable and is the ordinary JLCPCB default\n"
        "- order the half panel and daughterboard as separate assembly jobs\n\n"
        "The separate switch plates are specified as 1.5 mm POM. Supply the "
        "selected `plate/Symm60HE-plate-*-left.dxf` and matching `-right.dxf` "
        "without rescaling; the plate fabricator must apply its own kerf "
        "compensation. Each plate half must retain two short outer-edge "
        "gasket tongues and two matching short centre-side tongues. Cut the "
        "correspondingly named "
        "`plate/Symm60HE-gasket-pads-<layout>.dxf` from 1.5 mm Poron; the "
        "unsuffixed gasket-pad file is the universal-layout alias. All eight "
        "mounts use the same smooth-tapered 5 mm projection. The finished "
        "plate web is at least 2.0 mm; Hype does not publish a numeric web "
        "limit, so request their final DXF review before ordering.\n\n"
        "## Half-panel job\n\n"
        "Upload `Symm60HE-Half-Panel-Gerbers.zip` with "
        "`Symm60HE-Half-Panel/Symm60HE-Half-Panel-BOM.csv` and "
        "`Symm60HE-Half-Panel/Symm60HE-Half-Panel-CPL.csv`. All fitted SMT "
        "parts are on B.Cu. In the Gerber viewer confirm the 162.34 x 227.88 mm "
        "plotted bounds, routed panel outline, thirteen mouse-bite rows, four "
        "tooling holes, three fiducials, every LED aperture, and all four right-board "
        "routed NPTH alignment slots used by mutually exclusive layout positions. Do "
        "not pay if a slot is deleted, rendered as overlapping drill hits or plated.\n\n"
        "## Daughterboard job\n\n"
        "Upload `Symm60HE-Daughterboard-Gerbers.zip` with "
        "`Symm60HE-Daughterboard/Symm60HE-Daughterboard-BOM.csv` and "
        "`Symm60HE-Daughterboard/Symm60HE-Daughterboard-CPL.csv`. This is a "
        "mixed-side assembly. Confirm that the assembler quotes both sides and "
        "that the Gerber viewer reports approximately 50.1 x 31.1 mm plotted "
        "bounds, four perimeter M2 NPTH mounts, two outward-facing FPC sockets "
        "and the rear-facing USB-C opening.\n\n"
        "## Release identity\n\n"
        "Run `shasum -a 256 -c release/jlcpcb/SHA256SUMS.txt` from the project "
        "root immediately before upload. The manifest covers the two Gerber "
        "archives, both BOM/CPL pairs, this documentation, the exact source "
        "PCBs, the firmware binary and its clean-build report.\n\n"
        "Order prototype quantity first. Production quantity remains gated on "
        "physical plate/case/FFC fit and assembled Hall-noise testing.\n")
    # Cover the exact fabrication, assembly, firmware and source-board inputs.
    # Including source PCBs makes a later board edit visible even when a stale
    # ZIP still passes its own archive-integrity check.
    assembly_files = []
    for name, _ in targets:
        board_dir = release / name
        assembly_files.extend((
            board_dir / f"{name}-BOM.csv",
            board_dir / f"{name}-CPL.csv",
        ))
    source_boards = [ROOT / "pcb" / f"{board_name}.kicad_pcb"
                     for _, board_name in targets]
    manifest_paths = (archives + assembly_files + [readme, checklist] +
                      source_boards + [
        ROOT / "firmware/build/firmware.bin",
        ROOT / "release/reports/firmware-build.txt",
    ])
    manifest = release / "SHA256SUMS.txt"
    manifest.write_text("".join(f"{sha256(path)}  {path.relative_to(ROOT)}\n"
                                for path in manifest_paths))
    for archive in archives:
        with zipfile.ZipFile(archive) as zipped:
            bad = zipped.testzip()
            if bad:
                raise SystemExit(f"bad ZIP member: {archive}: {bad}")
        print(archive.relative_to(ROOT), sha256(archive))
    print(manifest.relative_to(ROOT))


if __name__ == "__main__":
    main()
