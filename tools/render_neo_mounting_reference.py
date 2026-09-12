#!/usr/bin/env python3
"""Render the Fusion-ready Neo pogo mounting reference from generated meshes."""
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "case/fusion360/pogo-neo-mounting-reference"
GEN = SRC / "generated"
OUT = ROOT / "docs/img/29-neo-pogo-mounting-reference.png"
EXPLODED = ROOT / "docs/img/30-neo-pogo-mounting-reference-exploded.png"


def colour(name):
    if "SpringTravelEnvelope" in name:
        return "[0.95,0.55,0.16,0.24]"
    if "PCB" in name or "HallPCBDatum" in name:
        return "[0.05,0.34,0.18,0.80]"
    if "SpringConnector" in name or "TargetConnector" in name:
        return "[0.82,0.60,0.18,1.0]"
    if "FFC" in name:
        return "[0.20,0.55,0.90,0.72]"
    if "CompressionStop" in name:
        return "[0.85,0.86,0.88,1.0]"
    if "Poron" in name:
        return "[0.12,0.12,0.14,1.0]"
    if "Hardware" in name:
        return "[0.68,0.70,0.73,1.0]"
    if "Ledge" in name or "Lip" in name:
        return "[0.36,0.48,0.72,1.0]"
    return "[0.28,0.46,0.66,1.0]"


def write_scad(path, meshes, exploded=False):
    lines = ["$fn=48;"]
    for mesh in meshes:
        dz = 0
        if exploded:
            if "HallPCBDatum" in mesh.stem:
                dz = 12
            elif "TargetConnector" in mesh.stem:
                dz = 8
            elif "SpringTravelEnvelope" in mesh.stem:
                dz = 2
            elif "CaptureLips" in mesh.stem or "CompressionStops" in mesh.stem:
                dz = 4
        lines.append(
            f'translate([0,0,{dz}]) color({colour(mesh.stem)}) '
            f'import("{mesh.as_posix()}");')
    path.write_text("\n".join(lines) + "\n")


def render(openscad, scad, output):
    subprocess.run([
        openscad, "-o", str(output), "--imgsize=2200,1350",
        "--projection=ortho", "--autocenter", "--viewall",
        "--camera=0,0,0,68,0,26,0", str(scad),
    ], check=True)


def main():
    openscad = shutil.which("openscad")
    if not openscad:
        raise RuntimeError("OpenSCAD not found")
    meshes = sorted(GEN.glob("*.stl"))
    if not meshes:
        raise RuntimeError("run export_neo_mounting_reference.py first")
    assembled_scad = GEN / "preview.scad"
    exploded_scad = GEN / "preview-exploded.scad"
    write_scad(assembled_scad, meshes)
    write_scad(exploded_scad, meshes, exploded=True)
    render(openscad, assembled_scad, OUT)
    render(openscad, exploded_scad, EXPLODED)
    print(OUT.relative_to(ROOT))
    print(EXPLODED.relative_to(ROOT))


if __name__ == "__main__":
    main()
