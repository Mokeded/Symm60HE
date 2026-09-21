#!/usr/bin/env python3
"""Create Gerber, drill, BOM and CPL packages for all fixed-layout halves."""
from __future__ import annotations

from pathlib import Path
import hashlib
import shutil
import subprocess
import zipfile

from layouts.make_layout_pcbs import LAYOUTS
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
        for side in ("Left", "Right"):
            stem = f"Symm60HE-{layout}-{side}"
            board = ROOT / "pcb/variants/layouts" / layout / f"{stem}.kicad_pcb"
            board_dir = release / layout / side
            gerbers = board_dir / "gerbers"
            gerbers.mkdir(parents=True)
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
            manifest_paths.extend((archive, drill_report, bom, cpl, board))
            print(f"{layout}/{side}: {archive.relative_to(ROOT)}")
    readme = release / "README.md"
    readme.write_text(
        "# Symm60HE fixed-layout PCB fabrication packages\n\n"
        "Each of the eight layout directories contains independent Left and Right "
        "Gerber ZIPs plus matching BOM, CPL and drill reports. Order as 2-layer, "
        "1.2 mm FR-4, 1 oz copper, black solder mask and white silkscreen. All "
        "alignment holes are ordinary circular NPTHs on these fixed-layout boards; "
        "the routed shared slots exist only on the universal right half. The BOM/CPL "
        "pairs omit every sensor, LED and support part not used by that physical "
        "layout. Confirm board outline, LED apertures, four M2 mounts and NPTH status "
        "in the fabricator viewer before payment.\n")
    manifest_paths.append(readme)
    manifest = release / "SHA256SUMS.txt"
    manifest.write_text("".join(
        f"{sha256(path)}  {path.relative_to(ROOT)}\n" for path in manifest_paths))
    print(manifest.relative_to(ROOT))


if __name__ == "__main__":
    main()
