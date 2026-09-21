"""Render current plate/gasket DXFs and assemble the generated image gallery."""
from pathlib import Path

import ezdxf
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon
from shapely.affinity import translate

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "gallery"
OUT.mkdir(parents=True, exist_ok=True)

BG = (15, 20, 28)
PLATE = (153, 164, 178)
EDGE = (224, 231, 239)
CUT = (8, 11, 17)
ACCENT = (85, 196, 220)
TEXT = (235, 240, 246)
SUB = (164, 176, 190)


def font(size, bold=False):
    names = (["/System/Library/Fonts/Supplemental/Arial Bold.ttf"] if bold else []) + [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/SFNS.ttf",
    ]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def polylines(path):
    doc = ezdxf.readfile(path)
    result = []
    for entity in doc.modelspace().query("LWPOLYLINE"):
        points = [(float(x), float(y)) for x, y, *_ in entity.get_points()]
        if len(points) >= 3:
            result.append((entity.dxf.layer, Polygon(points)))
    return result


def render_shapes(shapes, output, title, subtitle, gasket=False,
                  split_labels=False):
    bounds = [p.bounds for _, p in shapes]
    x0 = min(b[0] for b in bounds); y0 = min(b[1] for b in bounds)
    x1 = max(b[2] for b in bounds); y1 = max(b[3] for b in bounds)
    width, height, margin, header = 1800, 850, 75, 115
    supersample = 4
    scale = min((width - 2 * margin) / (x1 - x0),
                (height - header - 2 * margin) / (y1 - y0))
    ox = (width - (x1 - x0) * scale) / 2
    oy = header + (height - header - (y1 - y0) * scale) / 2

    def xy(point):
        return ((ox + (point[0] - x0) * scale) * supersample,
                (oy + (y1 - point[1]) * scale) * supersample)

    image = Image.new("RGB", (width * supersample,
                              height * supersample), BG)
    draw = ImageDraw.Draw(image)
    draw.text((55 * supersample, 28 * supersample), title,
              font=font(34 * supersample, True), fill=TEXT)
    draw.text((57 * supersample, 73 * supersample), subtitle,
              font=font(20 * supersample), fill=SUB)

    if gasket:
        for _, pad in shapes:
            draw.polygon([xy(p) for p in pad.exterior.coords], fill=ACCENT,
                         outline=EDGE)
    else:
        outlines = [p for layer, p in shapes if layer == "PLATE_OUTLINE"]
        for outline in outlines:
            draw.polygon([xy(p) for p in outline.exterior.coords], fill=PLATE,
                         outline=EDGE)
        for layer, poly in shapes:
            if layer == "PLATE_OUTLINE":
                continue
            draw.polygon([xy(p) for p in poly.exterior.coords], fill=CUT,
                         outline=ACCENT if layer == "STAB_CLEARANCE" else CUT)

    if split_labels:
        draw.rounded_rectangle(((width // 2 - 180) * supersample,
                                (height - 58) * supersample,
                                (width // 2 + 180) * supersample,
                                (height - 20) * supersample),
                               radius=18 * supersample, fill=(26, 35, 46))
        draw.text((width // 2 * supersample,
                   (height - 39) * supersample),
                  "independent halves — no centre bridge", anchor="mm",
                  font=font(17 * supersample, True), fill=ACCENT)

    image.resize((width, height), Image.Resampling.LANCZOS).save(output)
    return output


def render_dxf(path, output, title, subtitle, gasket=False):
    return render_shapes(polylines(path), output, title, subtitle, gasket)


def render_split_plate(left_path, right_path, output, title, subtitle):
    """Render the two fabrication files with a visible exploded-view gap."""
    gap = 9.0
    left = [(layer, translate(poly, xoff=-gap))
            for layer, poly in polylines(left_path)]
    right = [(layer, translate(poly, xoff=gap))
             for layer, poly in polylines(right_path)]
    return render_shapes(left + right, output, title,
                         subtitle + " · separate left/right DXFs",
                         split_labels=True)


plate_specs = [
    ("Symm60HE-plate-wkl", "plate-wkl.png", "Split plate — WKL",
     "60 switch openings · fixed 1.5u backspace layout"),
    ("Symm60HE-plate-wklbs2", "plate-wklbs2.png", "Split plate — WKL 2u backspace",
     "59 switch openings · fixed 2u backspace layout"),
    ("Symm60HE-plate-wklarrows", "plate-wklarrows.png", "Split plate — WKL arrows",
     "63 switch openings · dedicated arrow cluster"),
    ("Symm60HE-plate-wklbs2arrows", "plate-wklbs2arrows.png",
     "Split plate — WKL 2u backspace + arrows", "62 switch openings"),
    ("Symm60HE-plate-wkl-left-arrows-right",
     "plate-wkl-left-arrows-right.png",
     "Split plate — WKL left + arrows right",
     "mixed bottom rows · split Backspace"),
    ("Symm60HE-plate-three-key-left-wkl-right",
     "plate-three-key-left-wkl-right.png",
     "Split plate — three-key left + standard right",
     "mixed bottom rows · split Backspace"),
    ("Symm60HE-plate-wkl-left-arrows-right-bs2",
     "plate-wkl-left-arrows-right-bs2.png",
     "Split plate — WKL left + arrows right + 2u Backspace",
     "mixed bottom rows · 2u Backspace"),
    ("Symm60HE-plate-three-key-left-wkl-right-bs2",
     "plate-three-key-left-wkl-right-bs2.png",
     "Split plate — three-key left + standard right + 2u Backspace",
     "mixed bottom rows · 2u Backspace"),
    ("Symm60HE-plate-universal", "plate-universal.png", "Split universal plate",
     "57 merged openings · supports all four layouts"),
]

for stem, target, title, subtitle in plate_specs:
    render_split_plate(ROOT / "plate" / f"{stem}-left.dxf",
                       ROOT / "plate" / f"{stem}-right.dxf",
                       OUT / target, title, subtitle)

render_dxf(ROOT / "plate" / "Symm60HE-gasket-pads.dxf",
           OUT / "gasket-pads.png", "Integral-mount Poron gasket pads",
           "Eight matching short pads; two on each straight side wall",
           gasket=True)


def contact_sheet():
    files = [
        "pcb-left-top.png", "pcb-left-bottom.png",
        "pcb-right-top.png", "pcb-right-bottom.png",
        "pcb-daughterboard-top.png", "pcb-daughterboard-bottom.png",
        "pogo-left-spring-module-top.png",
        "pogo-left-spring-module-bottom.png",
        "pogo-right-spring-module-top.png",
        "pogo-right-spring-module-bottom.png",
        "plate-wkl.png", "plate-wklbs2.png", "plate-wklarrows.png",
        "plate-wklbs2arrows.png", "plate-wkl-left-arrows-right.png",
        "plate-three-key-left-wkl-right.png",
        "plate-wkl-left-arrows-right-bs2.png",
        "plate-three-key-left-wkl-right-bs2.png",
        "plate-universal.png", "gasket-pads.png",
        "mount-alignment-overlay.png",
    ]
    existing = [(name, Image.open(OUT / name).convert("RGB"))
                for name in files if (OUT / name).exists()]
    cell_w, cell_h, cols = 700, 455, 2
    rows = (len(existing) + cols - 1) // cols
    sheet = Image.new("RGB", (cell_w * cols, cell_h * rows + 80), BG)
    draw = ImageDraw.Draw(sheet)
    draw.text((28, 20), "Symm60HE — complete current artifact gallery",
              font=font(32, True), fill=TEXT)
    for i, (name, im) in enumerate(existing):
        col, row = i % cols, i // cols
        max_w, max_h = cell_w - 30, cell_h - 65
        im.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        x = col * cell_w + (cell_w - im.width) // 2
        y = 80 + row * cell_h + 35 + (max_h - im.height) // 2
        sheet.paste(im, (x, y))
        draw.text((col * cell_w + 18, 80 + row * cell_h + 8),
                  name.removesuffix(".png").replace("-", " "),
                  font=font(19, True), fill=TEXT)
    sheet.save(OUT / "00-complete-gallery.png")
    return len(existing)


if __name__ == "__main__":
    print("rendered nine split plate pairs and one gasket-pad pattern")
    print("contact sheet contains %d images" % contact_sheet())
