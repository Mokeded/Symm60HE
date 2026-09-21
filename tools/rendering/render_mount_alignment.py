#!/usr/bin/env python3
"""Render PCB and plate M2 holes in one shared coordinate system."""
from pathlib import Path
import sys

import ezdxf
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from route import read  # noqa: E402
from sexp import find, first, loads  # noqa: E402

OUT = ROOT / "docs/gallery/mount-alignment-overlay.png"
WIDTH, HEIGHT = 1900, 920
MARGIN, HEADER = 65, 125


def font(size, bold=False):
    candidates = (["/System/Library/Fonts/Supplemental/Arial Bold.ttf"]
                  if bold else [])
    candidates += ["/System/Library/Fonts/Supplemental/Arial.ttf"]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


def reference(footprint):
    return next((str(prop[2]) for prop in find(footprint, "property")
                 if len(prop) > 2 and str(prop[1]) == "Reference"), "")


def board_mounts(path, prefix):
    board = loads(path.read_text())
    mounts = {}
    for footprint in find(board, "footprint"):
        ref = reference(footprint)
        if ref.startswith(prefix):
            at = first(footprint, "at")
            mounts[ref] = (float(at[1]), float(at[2]))
    return mounts


def plate_shapes(path):
    doc = ezdxf.readfile(path)
    outlines, openings, mounts = [], [], []
    for entity in doc.modelspace().query("LWPOLYLINE"):
        points = [(float(x), float(y)) for x, y, *_ in entity.get_points()]
        if len(points) < 3:
            continue
        polygon = Polygon(points)
        if entity.dxf.layer == "PLATE_OUTLINE":
            outlines.append(polygon)
        elif entity.dxf.layer == "STANDOFF_HOLES":
            mounts.append(polygon)
        else:
            openings.append(polygon)
    return outlines, openings, mounts


def main():
    sides = []
    for side, prefix in (("left", "MHL"), ("right", "MHR")):
        pcb_path = ROOT / "pcb" / f"Symm60HE-{side.title()}.kicad_pcb"
        plate_path = ROOT / "plate" / f"Symm60HE-plate-universal-{side}.dxf"
        pcb_outline = read(str(pcb_path))[2]
        outlines, openings, plate_mounts = plate_shapes(plate_path)
        mounts = board_mounts(pcb_path, prefix)
        sides.append((side, pcb_outline, outlines, openings,
                      plate_mounts, mounts))

    bounds = [shape.bounds for _, pcb, outlines, *_ in sides
              for shape in [pcb] + outlines]
    x0 = min(bound[0] for bound in bounds)
    y0 = min(bound[1] for bound in bounds)
    x1 = max(bound[2] for bound in bounds)
    y1 = max(bound[3] for bound in bounds)
    scale = min((WIDTH - 2 * MARGIN) / (x1 - x0),
                (HEIGHT - HEADER - 2 * MARGIN) / (y1 - y0))
    ox = (WIDTH - (x1 - x0) * scale) / 2
    oy = HEADER + (HEIGHT - HEADER - (y1 - y0) * scale) / 2

    def xy(point):
        return (ox + (point[0] - x0) * scale,
                oy + (point[1] - y0) * scale)

    image = Image.new("RGB", (WIDTH, HEIGHT), (15, 20, 28))
    draw = ImageDraw.Draw(image, "RGBA")
    draw.text((55, 24), "PCB-to-plate M2 mount alignment",
              font=font(36, True), fill=(238, 242, 247, 255))
    draw.text((57, 74),
              "Same absolute XY coordinate system — cyan PCB drill over red plate hole",
              font=font(21), fill=(172, 184, 198, 255))

    for side, pcb, outlines, openings, plate_mounts, mounts in sides:
        for outline in outlines:
            draw.polygon([xy(point) for point in outline.exterior.coords],
                         fill=(153, 164, 178, 135),
                         outline=(225, 231, 239, 255), width=2)
        for opening in openings:
            draw.polygon([xy(point) for point in opening.exterior.coords],
                         fill=(15, 20, 28, 220))
        draw.line([xy(point) for point in pcb.exterior.coords],
                  fill=(85, 196, 220, 255), width=3, joint="curve")

        centres = [polygon.centroid for polygon in plate_mounts]
        for ref, point in sorted(mounts.items()):
            px, py = xy(point)
            nearest = min(centres, key=lambda centre:
                          ((centre.x - point[0]) ** 2 +
                           (centre.y - point[1]) ** 2))
            error = ((nearest.x - point[0]) ** 2 +
                     (nearest.y - point[1]) ** 2) ** 0.5
            qx, qy = xy((nearest.x, nearest.y))
            plate_radius = 1.1 * scale
            pcb_radius = 0.55 * scale
            draw.ellipse((qx - plate_radius, qy - plate_radius,
                          qx + plate_radius, qy + plate_radius),
                         outline=(255, 89, 89, 255), width=5)
            draw.ellipse((px - pcb_radius, py - pcb_radius,
                          px + pcb_radius, py + pcb_radius),
                         fill=(85, 196, 220, 255),
                         outline=(235, 250, 255, 255), width=2)
            draw.text((px + 10, py - 25), f"{ref}  error {error:.3f} mm",
                      font=font(15, True), fill=(255, 235, 235, 255))

        label_x = min(xy((pcb.bounds[0], pcb.bounds[1]))[0] + 8,
                      WIDTH - 180)
        draw.text((label_x, HEIGHT - 45), f"{side.upper()} HALF",
                  font=font(19, True), fill=(85, 196, 220, 255))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
