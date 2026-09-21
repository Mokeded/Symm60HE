#!/usr/bin/env python3
"""Render the fixed-tent pogo module from its separate generated STL bodies."""
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "case/fusion360/tenting-solution"
GEN = SRC / "generated"
OUT = ROOT / "docs/img/24-fixed-tent-pogo-module.png"
EXPLODED = ROOT / "docs/img/25-fixed-tent-pogo-module-exploded.png"


def colour(name):
    if "SpringTravelEnvelope" in name:
        return "[0.95,0.55,0.16,0.24]"
    if "PCB" in name or "TargetPlane" in name:
        return "[0.05,0.34,0.18,1.0]"
    if "Connector" in name:
        return "[0.82,0.60,0.18,1.0]"
    if "Guide" in name or "Stop" in name:
        return "[0.85,0.86,0.88,1.0]"
    if "Poron" in name:
        return "[0.12,0.12,0.14,1.0]"
    if "Magnet" in name:
        return "[0.72,0.20,0.24,0.75]"
    if "Clamp" in name:
        return "[0.36,0.48,0.72,1.0]"
    return "[0.28,0.46,0.66,1.0]"


def main():
    openscad = shutil.which("openscad")
    if not openscad:
        raise RuntimeError("OpenSCAD not found")
    meshes = sorted(GEN.glob("*.stl"))
    if not meshes:
        raise RuntimeError("run export_tenting_solution.py with freecadcmd first")
    scad = GEN / "preview.scad"
    scad.write_text("$fn=48;\n" + "\n".join(
        f'color({colour(path.stem)}) import("{path.as_posix()}");'
        for path in meshes) + "\n")
    subprocess.run([
        openscad, "-o", str(OUT), "--imgsize=2000,1200", "--projection=ortho",
        "--autocenter", "--viewall", "--camera=0,0,0,67,0,24,0", str(scad)
    ], check=True)
    exploded_scad = GEN / "preview-exploded.scad"
    exploded_lines = ["$fn=48;"]
    for path in meshes:
        name = path.stem
        dz = 0
        if "TargetPlane" in name or "TargetReceiver" in name:
            dz = 13
        elif "TargetConnector" in name:
            dz = 9
        elif "SpringTravelEnvelope" in name:
            dz = 2
        elif "Clamp" in name:
            dz = 5
        exploded_lines.append(
            f'translate([0,0,{dz}]) color({colour(name)}) import("{path.as_posix()}");')
    exploded_scad.write_text("\n".join(exploded_lines) + "\n")
    subprocess.run([
        openscad, "-o", str(EXPLODED), "--imgsize=2000,1200", "--projection=ortho",
        "--autocenter", "--viewall", "--camera=0,0,0,67,0,24,0",
        str(exploded_scad)
    ], check=True)
    print(OUT.relative_to(ROOT))
    print(EXPLODED.relative_to(ROOT))


if __name__ == "__main__":
    main()
