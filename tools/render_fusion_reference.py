#!/usr/bin/env python3
"""Render the integrated in-case Fusion reference for visual QA."""
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent
GEN = ROOT / "case/fusion360/generated"
OUT = ROOT / "docs/img/17-fusion-populated-reference.png"
DETAIL_OUT = ROOT / "docs/img/18-fusion-pogo-underside.png"
TOP_OUT = ROOT / "docs/img/20-fusion-daughterboards-top.png"
USB_OUT = ROOT / "docs/img/31-fusion-controller-usb-closeup.png"
GASKET_OUT = ROOT / "docs/img/32-fusion-interior-gasket-mounts.png"
SCAD = GEN / "populated-reference-preview.scad"
DETAIL_SCAD = GEN / "pogo-mechanism-preview.scad"
USB_SCAD = GEN / "controller-usb-closeup.scad"
GASKET_SCAD = GEN / "interior-gasket-mounts.scad"

PARTS = (
    ("LeftPCB", "[0.06,0.28,0.12,1]"),
    ("RightPCB", "[0.06,0.28,0.12,1]"),
    ("LeftPlate", "[0.58,0.62,0.68,0.48]"),
    ("RightPlate", "[0.58,0.62,0.68,0.48]"),
    ("LeftSwitches", "[0.10,0.10,0.12,0.85]"),
    ("RightSwitches", "[0.10,0.10,0.12,0.85]"),
    ("LeftKeycaps", "[0.78,0.83,0.88,0.75]"),
    ("RightKeycaps", "[0.78,0.83,0.88,0.75]"),
    ("DaughterboardPCB", "[0.04,0.22,0.09,1]"),
    ("ControllerUSBConnector", "[0.62,0.64,0.67,1]"),
    ("ControllerUSBPlugEnvelope", "[0.62,0.72,0.82,0.35]"),
    ("LeftSpringPCB", "[0.10,0.42,0.18,1]"),
    ("RightSpringPCB", "[0.10,0.42,0.18,1]"),
    ("LeftTargetConnector", "[0.90,0.72,0.15,1]"),
    ("RightTargetConnector", "[0.90,0.72,0.15,1]"),
    ("LeftSpringConnector", "[0.90,0.48,0.08,1]"),
    ("RightSpringConnector", "[0.90,0.48,0.08,1]"),
    ("LeftSpringFFCConnector", "[0.08,0.08,0.09,1]"),
    ("RightSpringFFCConnector", "[0.08,0.08,0.09,1]"),
    ("LeftControllerFFC", "[0.08,0.08,0.09,1]"),
    ("RightControllerFFC", "[0.08,0.08,0.09,1]"),
    ("LeftFFCEnvelope", "[0.10,0.70,0.82,0.75]"),
    ("RightFFCEnvelope", "[0.10,0.70,0.82,0.75]"),
)


def main():
    openscad = shutil.which("openscad")
    if not openscad:
        raise RuntimeError("OpenSCAD not found")
    paths = [(GEN / ("CaseRef-" + name + ".stl"), colour)
             for name, colour in PARTS]
    missing = [path.name for path, _ in paths if not path.is_file()]
    if missing:
        raise RuntimeError("missing integrated reference meshes: " + ", ".join(missing))
    SCAD.write_text("$fn=36;\n" + "\n".join(
        'color(%s) import("%s");' % (colour, path.as_posix())
        for path, colour in paths) + "\n")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        openscad, "-o", str(OUT), "--imgsize=2200,1400",
        "--projection=ortho", "--autocenter", "--viewall",
        "--camera=0,0,0,68,0,25,0", str(SCAD)
    ], check=True)
    detail_names = {
        "DaughterboardPCB", "ControllerUSBConnector",
        "ControllerUSBPlugEnvelope", "LeftSpringPCB", "RightSpringPCB",
        "LeftTargetConnector", "RightTargetConnector",
        "LeftSpringConnector", "RightSpringConnector",
        "LeftSpringFFCConnector", "RightSpringFFCConnector",
        "LeftControllerFFC", "RightControllerFFC",
        "LeftFFCEnvelope", "RightFFCEnvelope",
    }
    DETAIL_SCAD.write_text("$fn=36;\n" + "\n".join(
        'color(%s) import("%s");' % (colour, path.as_posix())
        for (name, colour), (path, _) in zip(PARTS, paths)
        if name in detail_names) + "\n")
    subprocess.run([
        openscad, "-o", str(DETAIL_OUT), "--imgsize=1800,1400",
        "--projection=ortho", "--autocenter", "--viewall",
        "--camera=0,0,0,248,0,25,0", str(DETAIL_SCAD)
    ], check=True)
    subprocess.run([
        openscad, "-o", str(TOP_OUT), "--imgsize=2200,1400",
        "--projection=ortho", "--autocenter", "--viewall",
        # Rotate the plan view so the keyboard rear/USB exit is at the top of
        # the documentation image, matching the normal keyboard convention.
        "--camera=0,0,0,0,0,180,0", str(DETAIL_SCAD)
    ], check=True)
    usb_names = {
        "DaughterboardPCB", "ControllerUSBConnector",
        "LeftControllerFFC", "RightControllerFFC",
    }
    USB_SCAD.write_text("$fn=48;\n" + "\n".join(
        'color(%s) import("%s");' % (colour, path.as_posix())
        for (name, colour), (path, _) in zip(PARTS, paths)
        if name in usb_names) + "\n")
    subprocess.run([
        openscad, "-o", str(USB_OUT), "--imgsize=1800,1200",
        "--projection=ortho", "--autocenter", "--viewall",
        # Look inward from negative Y at the rear case wall so the actual USB-C
        # mating mouth, rather than the connector's solder-tail side, is visible.
        "--camera=0,0,0,58,0,18,0", str(USB_SCAD)
    ], check=True)
    # Crop the two placed/tented plates to the centre kernel so the four inner
    # suspension tongues can be inspected without switches, PCBs or keycaps.
    left_plate = (GEN / "CaseRef-LeftPlate.stl").as_posix()
    right_plate = (GEN / "CaseRef-RightPlate.stl").as_posix()
    clip = "translate([128,-8,-20]) cube([47,122,70])"
    GASKET_SCAD.write_text(
        "$fn=48;\n"
        "color([0.45,0.62,0.82,1]) intersection() { "
        f'import("{left_plate}"); {clip}; }}\n'
        "color([0.78,0.82,0.88,1]) intersection() { "
        f'import("{right_plate}"); {clip}; }}\n')
    subprocess.run([
        openscad, "-o", str(GASKET_OUT), "--imgsize=1600,1800",
        "--projection=ortho", "--autocenter", "--viewall",
        "--camera=0,0,0,0,0,180,0", str(GASKET_SCAD)
    ], check=True)
    print("rendered", OUT.relative_to(ROOT))
    print("rendered", DETAIL_OUT.relative_to(ROOT))
    print("rendered", TOP_OUT.relative_to(ROOT))
    print("rendered", USB_OUT.relative_to(ROOT))
    print("rendered", GASKET_OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
