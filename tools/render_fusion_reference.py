#!/usr/bin/env python3
"""Render the populated Fusion reference assembly for documentation."""
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent
GEN = ROOT / "case/fusion360/generated"
OUT = ROOT / "docs/img/17-fusion-populated-reference.png"
SCAD = GEN / "populated-reference-preview.scad"

PARTS = (
    ("LeftPCB-placed.stl", "[0.08,0.30,0.14,1.0]"),
    ("RightPCB-placed.stl", "[0.08,0.30,0.14,1.0]"),
    ("DaughterboardPCB-placed.stl", "[0.05,0.22,0.10,1.0]"),
    ("LeftPlate-placed.stl", "[0.52,0.56,0.62,0.55]"),
    ("RightPlate-placed.stl", "[0.52,0.56,0.62,0.55]"),
    ("LeftSwitches-placed.stl", "[0.10,0.10,0.12,1.0]"),
    ("RightSwitches-placed.stl", "[0.10,0.10,0.12,1.0]"),
    ("LeftKeycaps-placed.stl", "[0.78,0.83,0.88,1.0]"),
    ("RightKeycaps-placed.stl", "[0.78,0.83,0.88,1.0]"),
)


def main():
    openscad = shutil.which("openscad")
    if not openscad:
        raise RuntimeError("OpenSCAD not found")
    missing = [name for name, _ in PARTS if not (GEN / name).is_file()]
    if missing:
        raise RuntimeError("missing placed Fusion meshes: " + ", ".join(missing))
    SCAD.write_text("$fn=36;\n" + "\n".join(
        f'color({colour}) import("{(GEN / name).as_posix()}");'
        for name, colour in PARTS) + "\n")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        openscad, "-o", str(OUT), "--imgsize=2000,1250",
        "--projection=ortho", "--autocenter", "--viewall",
        "--camera=0,0,0,62,0,24,0", str(SCAD)
    ], check=True)
    print("rendered", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
