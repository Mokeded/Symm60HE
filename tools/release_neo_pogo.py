#!/usr/bin/env python3
"""Generate complete BOM/CPL packages for the active Neo pogo PCB set.

The two Hall PCBs are universal, but their alternate bottom-row, arrow and
split-backspace positions cannot all be populated at once.  This exporter
therefore emits one pair of half-board assembly files per supported layout.
The controller and two floating spring modules are common to every layout.

For every board the package contains:

* a complete BOM and CPL, including the Mill-Max parts;
* a JLCPCB upload BOM and matching CPL containing every fitted SMT placement;
  exact Mill-Max MPNs are included with a blank LCSC field for manual matching;
* a validation summary tying the selected designators to the saved board.

The Mill-Max spring and target blocks have no locked LCSC number. They remain
explicit in the JLC upload files so the assembly portal can resolve them through
Global Sourcing, consignment, or a New Parts Request; they also remain in the
hand-install list until JLC confirms an assembly source.
"""
from collections import defaultdict
from pathlib import Path
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "pcb/variants/pogo-neo"
OUT = ROOT / "release/jlcpcb-pogo-neo"
SWITCH_MAP = ROOT / "Symm60HE-switch-map.csv"
SENSOR_ALIASES = ROOT / "Symm60HE-sensor-aliases.csv"

sys.path.insert(0, str(ROOT / "tools"))
from sexp import find, first, loads  # noqa: E402

LAYOUTS = ("doe-wkl", "doe-wklarrows", "doe-wklbs2",
           "doe-wklbs2arrows")
COMMON_BOARDS = (
    "Symm60HE-Neo-Controller",
    "Symm60HE-Neo-Left-SpringModule",
    "Symm60HE-Neo-Right-SpringModule",
)
HALF_BOARDS = {
    "Left": "Symm60HE-Neo-Left-Half",
    "Right": "Symm60HE-Neo-Right-Half",
}

# These are the project's locked sourcing selections.  Stock and basic/
# extended classification must still be refreshed in the assembly portal.
PARTS = {
    "MT9102ET": ("NOVOSENSE", "MT9102ET", "C5447698", "JLCPCB SMT"),
    "SN74LV4051A": ("Texas Instruments", "SN74LV4051ADR", "C128414", "JLCPCB SMT"),
    "100n": ("Samsung", "CL05B104KO5NNNC", "C1525", "JLCPCB SMT"),
    "4.7n": ("Murata", "GRM1555C1H472JE01D", "C1518204", "JLCPCB SMT"),
    "AT32F405RCT7": ("Artery", "AT32F405RCT7", "C47090415", "JLCPCB SMT"),
    "USBLC6-2SC6": ("STMicroelectronics", "USBLC6-2SC6", "C7519", "JLCPCB SMT"),
    "TLV75733PDBV": ("Texas Instruments", "TLV75733PDBVR", "C485517", "JLCPCB SMT"),
    "XC6206P332MR": ("Torex", "XC6206P332MR-G", "C5446", "JLCPCB SMT"),
    "12MHz": ("Yangxing", "X322512MSB4SI", "C9002", "JLCPCB SMT"),
    "0.5A": ("BHFUSE", "BSMD0805-050-24V", "C910822", "JLCPCB SMT"),
    "TS-1187A": ("XKB", "TS-1187A-B-A-B", "C318884", "JLCPCB SMT"),
    "12k": ("UNI-ROYAL", "0402WGF1202TCE", "C25752", "JLCPCB SMT"),
    "5.1k": ("UNI-ROYAL", "0402WGF5101TCE", "C25905", "JLCPCB SMT"),
    "10u": ("CCTC", "TCC0603X5R106M6R3CT", "C380318", "JLCPCB SMT"),
    "2.2u": ("Samsung", "CL10B225KP8NFNC", "C3905270", "JLCPCB SMT"),
    "1u": ("Murata", "GRM188R71A105KA61D", "C97888", "JLCPCB SMT"),
    "30p": ("CCTC", "TCC0402C0G300J500AT", "C466228", "JLCPCB SMT"),
    "FFC_12P": ("BOOMELE", "1.0-12P", "C20111", "JLCPCB SMT"),
    "FFC_12P_1.00mm": ("BOOMELE", "1.0-12P", "C20111", "JLCPCB SMT"),
    "TYPE-C-31-M-12": ("HRO", "TYPE-C-31-M-12", "C165948", "JLCPCB SMT"),
    "854-22-012-30-004101": (
        "Mill-Max", "854-22-012-30-004101", "", "Hand/consigned after reflow"),
    "856-10-012-30-051000": (
        "Mill-Max", "856-10-012-30-051000", "", "Hand/consigned after reflow"),
}


def find_cli():
    found = shutil.which("kicad-cli")
    if found:
        return found
    candidates = sorted(Path("/opt/homebrew/Caskroom/kicad").glob(
        "*/KiCad/KiCad.app/Contents/MacOS/kicad-cli"), reverse=True)
    if not candidates:
        raise RuntimeError("kicad-cli not found")
    return str(candidates[0])


def is_release_file(path):
    """Skip macOS metadata (AppleDouble ._*, .DS_Store) that a Mac copy leaves."""
    return path.is_file() and not path.name.startswith("._") and path.name != ".DS_Store"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def properties(fp):
    return {str(item[1]): str(item[2]) for item in find(fp, "property")
            if len(item) > 2}


def fitted_footprints(board_path):
    board = loads(board_path.read_text())
    result = {}
    for fp in find(board, "footprint"):
        attrs = [str(value) for value in (first(fp, "attr") or [])[1:]]
        props = properties(fp)
        reference = props.get("Reference", "")
        if (not reference or "smd" not in attrs or "board_only" in attrs or
                "exclude_from_bom" in attrs or "dnp" in attrs):
            continue
        result[reference] = {
            "reference": reference,
            "value": props.get("Value", ""),
            "footprint": str(fp[1]).split(":")[-1],
        }
    return result


def selected_half_refs(side, layout):
    short_layout = layout.removeprefix("doe-")
    selected = set()
    with SENSOR_ALIASES.open(newline="") as stream:
        aliases = {row["switch_ref"]: row["sensor_ref"]
                   for row in csv.DictReader(stream)}
    with SWITCH_MAP.open(newline="") as stream:
        for row in csv.DictReader(stream):
            if row["half"] != side[0] or short_layout not in row["in_builds"].split():
                continue
            index = int(row["ref"][3:])
            sensor_prefix = "HEL" if side == "Left" else "HER"
            cap_prefix = "CL" if side == "Left" else "CR"
            sensor_ref = aliases.get(row["ref"], f"{sensor_prefix}{index}")
            sensor_index = int(sensor_ref[3:])
            selected.update((sensor_ref, f"{cap_prefix}{sensor_index}A",
                             f"{cap_prefix}{sensor_index}B"))
    mux_prefix = "AML" if side == "Left" else "AMR"
    mux_cap_prefix = "CML" if side == "Left" else "CMR"
    selected.update(f"{mux_prefix}{index}" for index in range(1, 5))
    selected.update(f"{mux_cap_prefix}{index}" for index in range(1, 5))
    selected.add("PTL1" if side == "Left" else "PTR1")
    return selected


def export_positions(cli, board_path, output):
    raw = output.with_suffix(".kicad.csv")
    subprocess.run([
        cli, "pcb", "export", "pos", "--format", "csv", "--units", "mm",
        "--side", "both", "--smd-only", "--exclude-dnp", "-o", str(raw),
        str(board_path),
    ], check=True)
    with raw.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    raw.unlink()
    return rows


def sort_refs(refs):
    def key(ref):
        prefix = "".join(ch for ch in ref if not ch.isdigit())
        digits = "".join(ch for ch in ref if ch.isdigit())
        return prefix, int(digits or 0), ref
    return sorted(refs, key=key)


def write_bom(path, footprints, selected, jlc_only=False):
    grouped = defaultdict(list)
    for reference in selected:
        part = footprints[reference]
        if part["value"] not in PARTS:
            raise RuntimeError(f"No sourcing data for {part['value']} ({reference})")
        manufacturer, mpn, lcsc, assembly = PARTS[part["value"]]
        grouped[(part["value"], part["footprint"], manufacturer, mpn,
                 lcsc, assembly)].append(reference)
    with path.open("w", newline="") as stream:
        writer = csv.writer(stream)
        if jlc_only:
            writer.writerow(["Comment", "Designator", "Footprint", "LCSC Part #",
                             "Manufacturer", "Manufacturer Part Number"])
        else:
            writer.writerow(["Comment", "Designator", "Footprint", "Quantity",
                             "Manufacturer", "Manufacturer Part Number",
                             "LCSC Part #", "Assembly Method"])
        for key, refs in sorted(grouped.items()):
            value, footprint, manufacturer, mpn, lcsc, assembly = key
            refs = sort_refs(refs)
            if jlc_only:
                writer.writerow([value, ",".join(refs), footprint, lcsc,
                                 manufacturer, mpn])
            else:
                writer.writerow([value, ",".join(refs), footprint, len(refs),
                                 manufacturer, mpn, lcsc, assembly])


def write_cpl(path, position_rows, selected, jlc_only=False, footprints=None):
    rows = []
    for row in position_rows:
        reference = row["Ref"]
        if reference not in selected:
            continue
        rows.append(row)
    rows.sort(key=lambda row: sort_refs([row["Ref"]])[0])
    with path.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for row in rows:
            writer.writerow([row["Ref"], row["PosX"], row["PosY"],
                             "Top" if row["Side"] == "top" else "Bottom",
                             row["Rot"]])
    return {row["Ref"] for row in rows}


def emit_board(cli, stem, output, selected=None):
    board_path = SOURCE / f"{stem}.kicad_pcb"
    footprints = fitted_footprints(board_path)
    selected = set(footprints) if selected is None else set(selected)
    missing = selected - set(footprints)
    if missing:
        raise RuntimeError(f"{stem}: selected references missing: {sort_refs(missing)}")
    output.mkdir(parents=True, exist_ok=True)
    positions = export_positions(cli, board_path, output / f"{stem}-CPL.csv")
    position_refs = {row["Ref"] for row in positions}
    missing_positions = selected - position_refs
    if missing_positions:
        raise RuntimeError(f"{stem}: CPL positions missing: {sort_refs(missing_positions)}")

    full_bom = output / f"{stem}-BOM.csv"
    full_cpl = output / f"{stem}-CPL.csv"
    jlc_bom = output / f"{stem}-JLCPCB-BOM.csv"
    jlc_cpl = output / f"{stem}-JLCPCB-CPL.csv"
    write_bom(full_bom, footprints, selected)
    full_refs = write_cpl(full_cpl, positions, selected, footprints=footprints)
    write_bom(jlc_bom, footprints, selected, jlc_only=True)
    jlc_refs = write_cpl(jlc_cpl, positions, selected, jlc_only=True,
                         footprints=footprints)
    assert full_refs == selected
    expected_jlc = set(selected)
    assert jlc_refs == expected_jlc
    unmatched_refs = {ref for ref in selected
                      if not PARTS[footprints[ref]["value"]][2]}
    summary = {
        "source_board": str(board_path.relative_to(ROOT)),
        "selected_smt_placements": len(selected),
        "jlcpcb_smt_placements": len(jlc_refs),
        "unmatched_lcsc_placements": len(unmatched_refs),
        "hand_or_consigned_placements": len(unmatched_refs),
        "source_sha256": sha256(board_path),
        "files": [path.name for path in (full_bom, full_cpl, jlc_bom, jlc_cpl)],
    }
    (output / "assembly-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return footprints, selected


def write_set_bom(layout, assemblies, output):
    grouped = defaultdict(list)
    for board_name, footprints, selected in assemblies:
        for reference in selected:
            part = footprints[reference]
            manufacturer, mpn, lcsc, assembly = PARTS[part["value"]]
            grouped[(part["value"], part["footprint"], manufacturer, mpn,
                     lcsc, assembly)].append(f"{board_name}:{reference}")
    with output.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Comment", "Board-qualified Designators", "Footprint",
                         "Quantity per Keyboard", "Manufacturer",
                         "Manufacturer Part Number", "LCSC Part #",
                         "Assembly Method"])
        for key, refs in sorted(grouped.items()):
            value, footprint, manufacturer, mpn, lcsc, assembly = key
            writer.writerow([value, ",".join(sorted(refs)), footprint, len(refs),
                             manufacturer, mpn, lcsc, assembly])


def main():
    cli = find_cli()
    common = []
    for stem in COMMON_BOARDS:
        name = stem.removeprefix("Symm60HE-Neo-")
        footprints, selected = emit_board(cli, stem, OUT / "common" / name)
        common.append((name, footprints, selected))

    layout_manifest = {}
    for layout in LAYOUTS:
        assemblies = list(common)
        selected_counts = {}
        for side, stem in HALF_BOARDS.items():
            selected = selected_half_refs(side, layout)
            footprints, selected = emit_board(
                cli, stem, OUT / "layouts" / layout / side, selected)
            assemblies.append((side, footprints, selected))
            sensor_prefix = "HEL" if side == "Left" else "HER"
            selected_counts[side] = sum(ref.startswith(sensor_prefix)
                                        for ref in selected)
        write_set_bom(layout, assemblies,
                      OUT / "layouts" / layout / f"Symm60HE-Neo-{layout}-Set-BOM.csv")
        layout_manifest[layout] = selected_counts

    hand_install = OUT / "Symm60HE-Neo-Hand-Install-and-Cables.csv"
    with hand_install.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Item", "Manufacturer", "Manufacturer Part Number",
                         "Quantity per Keyboard", "Install location", "Notes"])
        writer.writerow(["12-contact spring connector", "Mill-Max",
                         "854-22-012-30-004101", 2, "PS1 on both spring modules",
                         "Hand/consigned; qualify coupon and reflow profile first"])
        writer.writerow(["12-contact target", "Mill-Max",
                         "856-10-012-30-051000", 2, "PTL1 and PTR1 on Hall PCBs",
                         "Hand/consigned; targets face the floating spring heads"])
        writer.writerow(["12-way 1.0 mm same-side FPC", "Custom flex PCB",
                         "TBD-after-case-route", 2, "Controller to spring modules",
                         "0.3 mm reinforced contact tails; finalize length, service loop and bend radius in case CAD"])

    manifest = {
        "variant": "Neo-style 12-contact direct-target pogo",
        "layouts": layout_manifest,
        "common_boards": list(COMMON_BOARDS),
        "coordinate_source": "KiCad 10 position exporter, millimetres",
        "mill_max_policy": "included in JLC upload BOM/CPL by exact MPN; blank LCSC requires manual sourcing match",
        "cpl_rotation_gate": "Confirm every orientation in the JLCPCB placement viewer",
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    readme = OUT / "README.md"
    readme.write_text(
        "# Symm60HE Neo-pogo BOM and CPL package\n\n"
        "This package is generated from the five active boards in "
        "`pcb/variants/pogo-neo`. The controller and two floating spring modules "
        "under `common/` are used by every build. Choose exactly one folder under "
        "`layouts/` for the left and right Hall-PCB assembly files.\n\n"
        "Each board directory contains a complete BOM/CPL and a matched "
        "`JLCPCB-BOM`/`JLCPCB-CPL` pair. The JLC pair includes the Mill-Max spring "
        "and target connector placements by exact manufacturer part number. Their "
        "LCSC fields are intentionally blank because no JLC/LCSC selection has "
        "been verified. Resolve those lines through Global Sourcing, consignment "
        "or a New Parts Request in the component-matching screen. They also remain "
        "in `Symm60HE-Neo-Hand-Install-and-Cables.csv` as the fallback until JLC "
        "confirms placement.\n\n"
        "The four half-board variants prevent mutually exclusive universal-layout "
        "sensor positions from being populated together. Do not combine files from "
        "different layout folders. Upload each JLCPCB BOM together with the CPL of "
        "the identical basename, refresh stock/substitution status, and confirm "
        "polarity, pin 1, side and rotation for every line in the placement viewer. "
        "The coordinate files come directly from KiCad 10 in millimetres; they do "
        "not replace the assembler's visual orientation check.\n\n"
        "These files describe assembly only. Gerbers and drills must be regenerated "
        "from the same board revisions before ordering. The pogo interface still "
        "requires connector-fit, Hall-noise, compression and endurance prototypes.\n")

    outputs = sorted(path for path in OUT.rglob("*") if is_release_file(path) and
                     path.name != "SHA256SUMS.txt")
    (OUT / "SHA256SUMS.txt").write_text("".join(
        f"{sha256(path)}  {path.relative_to(OUT)}\n" for path in outputs))
    archive = ROOT / "release/Symm60HE-Neo-Pogo-BOM-CPL.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
        for path in sorted(filter(is_release_file, OUT.rglob("*"))):
            zipped.write(path, Path(OUT.name) / path.relative_to(OUT))
    archive_hash = ROOT / "release/Symm60HE-Neo-Pogo-BOM-CPL.zip.sha256"
    archive_hash.write_text(f"{sha256(archive)}  {archive.name}\n")
    print(OUT.relative_to(ROOT))
    print(archive.relative_to(ROOT), sha256(archive))
    for layout, counts in layout_manifest.items():
        print(layout, counts)


if __name__ == "__main__":
    main()
