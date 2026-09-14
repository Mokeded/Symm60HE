#!/usr/bin/env python3
"""Close-up renders of the seated 854/856 pair, straight from the assembly meshes."""
from pathlib import Path
import subprocess

import numpy as np

from pogo_mate_geometry import SPRING, TARGET, load_stl, mating_frame, measure

ROOT = Path(__file__).resolve().parent.parent
GEN = ROOT / "case/fusion360/generated"
IMG = ROOT / "docs/img"
BUILD = ROOT / "case/fusion360/generated"

PARTS = {
    "spring": (GEN / "CaseRef-LeftSpringConnector.stl", "[0.82,0.60,0.18,1.0]"),
    "target": (GEN / "CaseRef-LeftTargetConnector.stl", "[0.12,0.44,0.55,1.0]"),
    "module": (GEN / "CaseRef-LeftSpringPCB.stl", "[0.05,0.34,0.18,0.90]"),
}
HALL = GEN / "CaseRef-LeftPCB.stl"
CROP = 11.0          # half-width of the window kept around the connector


def connector_frame():
    spring = load_stl(SPRING)
    rot, _ = mating_frame(spring)
    pts = np.vstack([spring.reshape(-1, 3), load_stl(TARGET).reshape(-1, 3)])
    return rot[2], pts.mean(axis=0)


def write_scad(path, explode):
    axis, centre = connector_frame()
    shift = axis * explode
    lines = ["$fn=64;"]
    for name, (mesh, colour) in PARTS.items():
        offset = shift if name == "target" else np.zeros(3)
        lines.append(f'color({colour}) translate([{offset[0]:.4f},{offset[1]:.4f},'
                     f'{offset[2]:.4f}]) import("{mesh}");')
    # The Hall PCB is the whole half board; keep only the part near the connector.
    lines.append(f'color([0.05,0.34,0.18,0.90]) translate([{shift[0]:.4f},'
                 f'{shift[1]:.4f},{shift[2]:.4f}]) intersection() {{')
    lines.append(f'  import("{HALL}");')
    lines.append(f'  translate([{centre[0]:.4f},{centre[1]:.4f},{centre[2]:.4f}])'
                 f' cube([{CROP},{CROP * 2.2},{CROP}], center=true);')
    lines.append("}")
    path.write_text("\n".join(lines) + "\n")
    return centre


def render(scad, png, centre, distance, rotation):
    camera = (f"{centre[0]:.3f},{centre[1]:.3f},{centre[2]:.3f},"
              f"{rotation[0]},{rotation[1]},{rotation[2]},{distance}")
    subprocess.run(["openscad", "-o", str(png), "--imgsize=1800,1250",
                    f"--camera={camera}", "--colorscheme=Tomorrow",
                    "--projection=perspective", str(scad)], check=True)


def main():
    geo = measure()
    IMG.mkdir(parents=True, exist_ok=True)
    for explode, name, distance, lift in [
            (0.0, "40-pogo-mate-3d-seated.png", 40, 0.0),
            (5.0, "41-pogo-mate-3d-exploded.png", 46, 2.4)]:
        scad = BUILD / (Path(name).stem + ".scad")
        centre = write_scad(scad, explode)
        axis, _ = connector_frame()
        render(scad, IMG / name, centre + axis * lift, distance, (68, 0, 28))
    print(f"board-to-board {geo.board_to_board:.4f} mm; wrote 40/41 to {IMG}")


if __name__ == "__main__":
    main()
