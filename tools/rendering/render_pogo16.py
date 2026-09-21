#!/usr/bin/env python3
"""Render pogo16 qualification coupons and the tent-cradle reference."""
from pathlib import Path
import shutil
import subprocess

from shapely.geometry import box
from img import BG, CU_COL, DIM, INK, Canvas, draw_copper, parts

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/img"


def coupon(kind, image):
    pcb = ROOT / "pcb/variants/pogo/coupon" / f"Symm60HE-Pogo16-{kind}-Coupon.kicad_pcb"
    canvas = Canvas(box(0, 0, 18, 28).bounds, 760, pad=28, foot=70)
    canvas.poly(box(0, 0, 18, 28), fill=(29, 90, 70), outline=(87, 211, 154), w=1.2)
    segments, vias = draw_copper(canvas, str(pcb), alpha=235)
    for ref, colour, shapes, at in parts(str(pcb)):
        for shape in shapes:
            canvas.poly(shape, fill=colour + (245,))
    fy = canvas.im.height / 3 - 51
    canvas.raw_text((18, fy), f"Pogo16 {kind.lower()} qualification coupon", INK, 10)
    canvas.raw_text((18, fy + 17), "Mill-Max 2x8 / 1.27 mm / power-off-only", DIM, 8.5)
    canvas.raw_text((18, fy + 33), f"{segments} routed segments, {vias} vias", CU_COL["F.Cu"], 8.5)
    print(image, canvas.save(image))


def mechanics():
    openscad = shutil.which("openscad")
    if not openscad:
        raise RuntimeError("OpenSCAD not found")
    source = ROOT / "case/fusion360/pogo-variant/Symm60HE-pogo16-tent-cradle.stl"
    scad = ROOT / "case/fusion360/pogo-variant/pogo16-preview.scad"
    scad.write_text(
        "$fn=48;\n"
        f'color([0.35,0.55,0.72]) import("{source.as_posix()}");\n')
    subprocess.run([
        openscad, "-o", str(OUT / "23-pogo16-tent-cradle.png"),
        "--imgsize=1800,1000", "--projection=ortho", "--autocenter", "--viewall",
        "--camera=0,0,0,65,0,25,0", str(scad)
    ], check=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    coupon("Spring", "21-pogo16-spring-coupon.png")
    coupon("Target", "22-pogo16-target-coupon.png")
    mechanics()
    print("rendered pogo16 reference images")


if __name__ == "__main__":
    main()
