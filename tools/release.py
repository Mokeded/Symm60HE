#!/usr/bin/env python3
"""Create deterministic JLCPCB fabrication/placement release artifacts."""
from collections import defaultdict
from pathlib import Path
import csv
import hashlib
import shutil
import subprocess
import zipfile

from mkschematics import components
from sexp import find, first, loads
from verify import ROOT, find_kicad_cli

LAYERS = "F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts"
LAYOUTS = ("doe-wkl", "doe-wklarrows", "doe-wklbs2",
           "doe-wklbs2arrows")


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


def write_board_bom(name, output, selected=None):
    grouped = defaultdict(list)
    descriptions = {}
    board_path = ROOT / "pcb" / f"{name}.kicad_pcb"
    board = loads(board_path.read_text())
    smt_refs = set()
    for fp in find(board, "footprint"):
        attr = first(fp, "attr")
        if not attr or "smd" not in attr[1:] or "board_only" in attr[1:]:
            continue
        reference = next((p[2] for p in find(fp, "property")
                          if len(p) > 2 and p[1] == "Reference"), "")
        if reference:
            smt_refs.add(str(reference))
    for part in components(board_path):
        if part["ref"] not in smt_refs or (selected is not None and
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
        if board_name == "Symm60HE-Panel":
            for layout in LAYOUTS:
                layout_dir = board_dir / "layouts" / layout
                layout_dir.mkdir(parents=True)
                selected = panel_layout_refs(layout)
                write_board_bom(board_name,
                                layout_dir / f"{name}-{layout}-BOM.csv",
                                selected)
                filter_cpl(raw_cpl,
                           layout_dir / f"{name}-{layout}-CPL.csv",
                           selected)
            raw_cpl.unlink()
        else:
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
        "as a 175.32 x 233.91 mm stacked panel with 5 mm routed rails, thirteen "
        "5-hole mouse-bite rows at 0.75 mm pitch, three global B.Cu fiducials, four "
        "2 mm tooling holes and all SMT components on B.Cu. Order that ZIP as one "
        "assembled PCB. Order the compact mixed-side daughterboard separately with "
        "`Symm60HE-Daughterboard-Gerbers.zip`; it has three local fiducials on each "
        "assembly side. Both designs are 2-layer, 1.2 mm finished thickness. The "
        "generated BOMs contain only fitted SMT parts and every line has an exact "
        "LCSC assignment. Choose exactly one matched BOM/CPL pair under the half-"
        "panel's `layouts/` directory; the universal panel must not be assembled "
        "from an all-positions placement list.\n\n"
        "Gerbers include both copper layers, both solder masks, both silkscreens and "
        "Edge.Cuts. Silkscreen was clipped to solder-mask openings during plotting.\n\n"
        "The panel's right board universal-layout arrow/2.25u-shift alternatives contain one "
        "pair of tangent NPTH holes. Confirm this merged/tangent drill geometry in JLC's "
        "Gerber viewer before payment; use a layout-specific PCB if JLC rejects it.\n")
    manifest_paths = archives + [readme, ROOT / "firmware/build/firmware.bin"]
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
