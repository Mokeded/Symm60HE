#!/usr/bin/env python3
"""Build a prototype-only fabrication pack for the 16-contact pogo coupons."""
from pathlib import Path
import csv
import hashlib
import shutil
import subprocess
import zipfile

from verify import ROOT, find_kicad_cli

BOARDS = ("Spring", "Target")
LAYERS = "F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    cli = find_kicad_cli()
    if not cli:
        raise SystemExit("kicad-cli not found")
    source = ROOT / "pcb/variants/pogo/coupon"
    release = ROOT / "release/pogo16-prototype"
    if release.exists():
        shutil.rmtree(release)
    release.mkdir(parents=True)
    outputs = []
    for side in BOARDS:
        stem = f"Symm60HE-Pogo16-{side}-Coupon"
        board = source / f"{stem}.kicad_pcb"
        target = release / stem
        gerbers = target / "gerbers"
        gerbers.mkdir(parents=True)
        subprocess.run([cli, "pcb", "drc", "--severity-error", "--exit-code-violations",
                        "-o", str(target / "drc.rpt"), str(board)], check=True)
        subprocess.run([cli, "pcb", "export", "gerbers", "--layers", LAYERS,
                        "-o", str(gerbers), str(board)], check=True)
        subprocess.run([cli, "pcb", "export", "drill", "--format", "excellon",
                        "--excellon-units", "mm", "-o", str(gerbers), str(board)], check=True)
        with (target / "BOM.csv").open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["Comment", "Designator", "Manufacturer", "MPN", "Assembly"])
            if side == "Spring":
                writer.writerow(["16-contact 2x8 SMT spring connector", "PS1", "Mill-Max",
                                 "855-22-016-30-004101", "Hand fit after coupon inspection"])
            else:
                writer.writerow(["16-contact 2x8 SMT gold target", "PT1", "Mill-Max",
                                 "857-10-016-30-051000", "Hand fit after coupon inspection"])
        archive = release / f"{stem}-Gerbers.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(gerbers.iterdir()):
                if path.name.startswith("._") or path.name == ".DS_Store":
                    continue  # macOS metadata from a Mac copy
                zf.write(path, path.name)
        outputs.append(archive)
    readme = release / "README.md"
    readme.write_text(
        "# Symm60HE 16-contact pogo qualification coupons\n\n"
        "PROTOTYPE ONLY - these are not the keyboard PCB release. Order one spring and one "
        "target coupon at 1.6 mm thickness, install the exact Mill-Max parts listed in each "
        "BOM, and use them to validate land geometry, reflow, alignment, 6.0 mm mid-stroke "
        "stack height, continuity and tolerance before integrating the interface. Mate and "
        "unmate only with USB power removed. The 2.25 mm guide holes and asymmetric 2.85 mm "
        "key hole are mechanical references for the matching carrier.\n")
    outputs.append(readme)
    manifest = release / "SHA256SUMS.txt"
    manifest.write_text("".join(f"{digest(p)}  {p.relative_to(ROOT)}\n" for p in outputs))
    print(release.relative_to(ROOT))


if __name__ == "__main__":
    main()
