#!/usr/bin/env python3
"""Render the populated Fusion reference assembly for documentation."""
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
GEN = ROOT / "case/fusion360/generated"
OUT = ROOT / "docs/img/17-fusion-populated-reference.png"
OUT_CABLING = ROOT / "docs/img/17b-fusion-cabling-reference.png"
OUT_CABLING_TOP = ROOT / "docs/img/17g-fusion-cabling-top-reference.png"
OUT_CABLE_ENTRY = ROOT / "docs/img/17h-fusion-daughterboard-cable-entry.png"
OUT_TRUE_TOP = ROOT / "docs/img/17j-fusion-true-top-reference.png"
SCAD = GEN / "populated-reference-preview.scad"
CABLE_SCAD = GEN / "cabling-reference-preview.scad"
CABLE_ENTRY_SCAD = GEN / "daughterboard-cable-entry-preview.scad"
TRUE_TOP_SCAD = GEN / "true-top-reference-preview.scad"

INSPECTION_VIEWS = (
    ("17c-fusion-rear-reference.png", "0,0,0,62,0,204,0"),
    ("17d-fusion-left-reference.png", "0,0,0,70,0,110,0"),
    ("17e-fusion-right-reference.png", "0,0,0,70,0,-70,0"),
    ("17f-fusion-top-reference.png", "0,0,0,0,0,0,0"),
)

PARTS = (
    ("LeftPCB-placed.stl", "[0.08,0.30,0.14,1.0]"),
    ("RightPCB-placed.stl", "[0.08,0.30,0.14,1.0]"),
    ("DaughterboardPCB-placed.stl", "[0.05,0.22,0.10,1.0]"),
    ("LeftPCBComponents-placed.stl", "[0.24,0.25,0.28,1.0]"),
    ("RightPCBComponents-placed.stl", "[0.24,0.25,0.28,1.0]"),
    ("DaughterboardPCBComponents-placed.stl", "[0.24,0.25,0.28,1.0]"),
    ("LeftRibbonCable-placed.stl", "[0.18,0.50,0.92,0.78]"),
    ("RightRibbonCable-placed.stl", "[0.18,0.50,0.92,0.78]"),
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
    # The assembly is physically tilted rear-up by seven degrees. Counteract
    # only that common X rotation for a plan-inspection image; retain the real
    # +/-3 degree lateral tent of the two halves.
    TRUE_TOP_SCAD.write_text(
        "$fn=36;\nrotate([7,0,0]) {\n" + "\n".join(
            f'  color({colour}) import("{(GEN / name).as_posix()}");'
            for name, colour in PARTS) + "\n}\n")
    cable_parts = PARTS[:8]
    CABLE_SCAD.write_text("$fn=36;\n" + "\n".join(
        f'color({colour}) import("{(GEN / name).as_posix()}");'
        for name, colour in cable_parts) + "\n")
    daughter = (GEN / "DaughterboardPCB-placed.stl").as_posix()
    daughter_components = (
        GEN / "DaughterboardPCBComponents-placed.stl").as_posix()
    left_ribbon = (GEN / "LeftRibbonCable-placed.stl").as_posix()
    right_ribbon = (GEN / "RightRibbonCable-placed.stl").as_posix()
    CABLE_ENTRY_SCAD.write_text(
        "$fn=36;\n"
        f'color([0.05,0.22,0.10,1.0]) import("{daughter}");\n'
        f'color([0.24,0.25,0.28,1.0]) import("{daughter_components}");\n'
        "color([0.18,0.50,0.92,0.82]) intersection() {\n"
        "  union() {\n"
        f'    import("{left_ribbon}");\n'
        f'    import("{right_ribbon}");\n'
        "  }\n"
        "  translate([112,-12,0]) cube([78,45,30]);\n"
        "}\n")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        openscad, "-o", str(OUT), "--imgsize=2000,1250",
        "--projection=ortho", "--autocenter", "--viewall",
        "--camera=0,0,0,62,0,24,0", str(SCAD)
    ], check=True)
    print("rendered", OUT.relative_to(ROOT))
    subprocess.run([
        openscad, "-o", str(OUT_CABLING), "--imgsize=1800,1200",
        "--projection=ortho", "--autocenter", "--viewall",
        "--camera=0,0,0,180,0,0,0", str(SCAD)
    ], check=True)
    print("rendered", OUT_CABLING.relative_to(ROOT))
    subprocess.run([
        openscad, "-o", str(OUT_CABLING_TOP), "--imgsize=1800,1200",
        "--projection=ortho", "--autocenter", "--viewall",
        "--camera=0,0,0,0,0,0,0", str(CABLE_SCAD)
    ], check=True)
    print("rendered", OUT_CABLING_TOP.relative_to(ROOT))
    subprocess.run([
        openscad, "-o", str(OUT_CABLE_ENTRY), "--imgsize=1600,1100",
        "--projection=ortho", "--autocenter", "--viewall",
        "--camera=0,0,0,58,0,25,0", str(CABLE_ENTRY_SCAD)
    ], check=True)
    print("rendered", OUT_CABLE_ENTRY.relative_to(ROOT))
    for filename, camera in INSPECTION_VIEWS:
        output = ROOT / "docs/img" / filename
        subprocess.run([
            openscad, "-o", str(output), "--imgsize=1800,1200",
            "--projection=ortho", "--autocenter", "--viewall",
            f"--camera={camera}", str(SCAD)
        ], check=True)
        print("rendered", output.relative_to(ROOT))
    subprocess.run([
        openscad, "-o", str(OUT_TRUE_TOP), "--imgsize=2000,1400",
        "--projection=ortho", "--autocenter", "--viewall",
        "--camera=0,0,0,0,0,0,0", str(TRUE_TOP_SCAD)
    ], check=True)
    print("rendered", OUT_TRUE_TOP.relative_to(ROOT))


if __name__ == "__main__":
    main()
