#!/usr/bin/env python3
"""Create one two-half Gerber, drill, BOM and CPL package per fixed layout."""
from __future__ import annotations

from pathlib import Path
import hashlib
import shutil
import subprocess
import zipfile

from layouts.catalog import LAYOUTS
from releases.release import LAYERS, write_board_bom
from verify import ROOT, find_kicad_cli


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    cli = find_kicad_cli()
    if not cli:
        raise SystemExit("kicad-cli not found")
    release = ROOT / "release/layout-pcbs"
    if release.exists():
        shutil.rmtree(release)
    release.mkdir(parents=True)
    manifest_paths = []
    for layout in LAYOUTS:
        stem = f"Symm60HE-{layout}-Panel"
        board = ROOT / "pcb/variants/layouts" / layout / f"{stem}.kicad_pcb"
        board_dir = release / layout
        gerbers = board_dir / "gerbers"
        gerbers.mkdir(parents=True)
        drc_report = board_dir / "drc-report.txt"
        subprocess.run([
            cli, "pcb", "drc", "--refill-zones", "--exit-code-violations",
            "--severity-all", "--format", "report", "--output",
            str(drc_report), str(board)], check=True)
        schematic = board.with_suffix(".kicad_sch")
        symbols = board.with_suffix(".kicad_sym")
        project = board.with_suffix(".kicad_pro")
        erc_report = board_dir / "erc-report.txt"
        subprocess.run([
            cli, "sch", "erc", "--exit-code-violations", "--severity-all",
            "--format", "report", "--output", str(erc_report),
            str(schematic)], check=True)
        subprocess.run([
            cli, "pcb", "export", "gerbers", "--layers", LAYERS,
            "--subtract-soldermask", "--check-zones", "-o", str(gerbers),
            str(board)], check=True)
        drill_report = board_dir / "drill-report.txt"
        subprocess.run([
            cli, "pcb", "export", "drill", "--format", "excellon",
            "--excellon-units", "mm", "--excellon-separate-th",
            "--generate-report", "--report-path", str(drill_report),
            "-o", str(gerbers), str(board)], check=True)
        cpl = board_dir / f"{stem}-CPL.csv"
        subprocess.run([
            cli, "pcb", "export", "pos", "--format", "csv", "--units", "mm",
            "--side", "both", "--exclude-dnp", "-o", str(cpl), str(board)],
            check=True)
        bom = board_dir / f"{stem}-BOM.csv"
        write_board_bom(stem, bom, board_path=board)
        archive = board_dir / f"{stem}-Gerbers.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
            for path in sorted(gerbers.iterdir()):
                zipped.write(path, path.name)
        with zipfile.ZipFile(archive) as zipped:
            bad = zipped.testzip()
            if bad:
                raise RuntimeError(f"bad ZIP member: {archive}: {bad}")
        left = board.with_name(f"Symm60HE-{layout}-Left.kicad_pcb")
        right = board.with_name(f"Symm60HE-{layout}-Right.kicad_pcb")
        manifest_paths.extend((archive, drill_report, drc_report, erc_report,
                               bom, cpl, board, schematic, symbols, project,
                               left, right))
        print(f"{layout}: {archive.relative_to(ROOT)}")
    readme = release / "README.md"
    readme.write_text(
        "# Symm60HE fixed-layout PCB fabrication packages\n\n"
        "Each of the eight layout directories is one complete two-design customer "
        "panel: a stacked left/right pair with routed rails and mouse-bite tabs, plus "
        "one matching BOM, CPL, drill report, zero-finding DRC report and "
        "zero-finding combined-schematic ERC report. Upload and "
        "order only the `*-Panel-"
        "Gerbers.zip` for the selected layout; do not order the source halves "
        "separately. Specify two different designs when quoting customer "
        "panelization. Order as 2-layer, 1.2 mm FR-4, 1 oz copper, black solder "
        "mask and white silkscreen. All alignment holes are ordinary circular "
        "NPTHs on these fixed-layout boards; the routed shared slots exist only "
        "on the universal right half. The panel BOM/CPL omits every sensor, LED "
        "and support part not used by that physical layout. Confirm both board "
        "outlines, every LED aperture, eight total M2 mounts, thirteen mouse-bite "
        "rows, three fiducials, four tooling holes and NPTH status in the "
        "fabricator viewer before payment.\n")
    manifest_paths.append(readme)
    manifest = release / "SHA256SUMS.txt"
    manifest.write_text("".join(
        f"{sha256(path)}  {path.relative_to(ROOT)}\n" for path in manifest_paths))
    print(manifest.relative_to(ROOT))


if __name__ == "__main__":
    main()
