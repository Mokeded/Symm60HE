#!/usr/bin/env python3
"""Render the two floating Neo-style pogo spring heads as one image."""
from pathlib import Path
import tempfile
import sys

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import box

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from img import Canvas, SS, draw_copper, parts  # noqa: E402


def render_board(path, output):
    # All four module generators use the same exact rectangular Edge.Cuts.
    # Use that controlled outline directly because KiCad may reorder its four
    # gr_line records when saving, while the legacy image helper assumes order.
    outline = box(0, 0, 20, 20)
    canvas = Canvas(outline.bounds, 720, pad=30, foot=0)
    canvas.poly(outline, fill=(29, 90, 70), outline=(87, 211, 154), w=1.1)
    draw_copper(canvas, str(path), alpha=235)
    for _, colour, shapes, _ in parts(str(path)):
        for shape in shapes:
            canvas.poly(shape, fill=colour + (245,))
    rendered = canvas.im.resize((canvas.im.width // SS, canvas.im.height // SS),
                                Image.Resampling.LANCZOS)
    rendered.save(output)


def main():
    out = ROOT / "docs/img/28-neo-pogo-modules.png"
    names = [(side, "Spring") for side in ("Left", "Right")]
    with tempfile.TemporaryDirectory(prefix="symm60he-neo-render-") as temp:
        images = []
        for side, kind in names:
            path = ROOT / "pcb/variants/pogo-neo" / \
                f"Symm60HE-Neo-{side}-{kind}Module.kicad_pcb"
            png = Path(temp) / f"{side}-{kind}.png"
            render_board(path, png)
            images.append((side, kind, Image.open(png).convert("RGB")))
        cell_w = max(image.width for _, _, image in images)
        cell_h = max(image.height for _, _, image in images) + 54
        sheet = Image.new("RGB", (cell_w * 2, cell_h + 68), (13, 20, 28))
        draw = ImageDraw.Draw(sheet)
        font = ImageFont.load_default()
        draw.text((24, 18), "Symm60HE Neo-style floating pogo spring heads",
                  fill=(232, 238, 242), font=font)
        draw.text((24, 38),
                  "12 contacts; one short FFC per head; targets mount directly on the Hall PCBs",
                  fill=(155, 175, 188), font=font)
        for index, (side, kind, image) in enumerate(images):
            x = index * cell_w
            y = 68
            sheet.paste(image, (x + (cell_w - image.width)//2, y + 32))
            draw.text((x + 20, y + 8), f"{side} {kind} module",
                      fill=(230, 190, 105), font=font)
        out.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(out)
    print(out.relative_to(ROOT))


if __name__ == "__main__":
    main()
