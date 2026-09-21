#!/usr/bin/env python3
"""Render top views of all fixed-layout PCB halves and paired comparisons."""
from pathlib import Path
import subprocess
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from layouts.make_layout_pcbs import LAYOUTS  # noqa: E402
from verify import find_kicad_cli  # noqa: E402

OUT = ROOT / "docs/gallery/layout-variants"


def main():
    cli = find_kicad_cli()
    if not cli:
        raise RuntimeError("kicad-cli not found")
    OUT.mkdir(parents=True, exist_ok=True)
    for layout in LAYOUTS:
        images = []
        for side in ("Left", "Right"):
            board = (ROOT / "pcb/variants/layouts" / layout /
                     f"Symm60HE-{layout}-{side}.kicad_pcb")
            output = OUT / f"{layout}-{side.lower()}-top.png"
            subprocess.run([
                cli, "pcb", "render", "--side", "top",
                "--width", "1488", "--height", "984",
                "--quality", "high", "--background", "opaque",
                "--use-board-stackup-colors", "-o", str(output),
                str(board),
            ], check=True)
            images.append(Image.open(output).convert("RGB"))
        pair = Image.new("RGB", (sum(image.width for image in images),
                                 max(image.height for image in images)))
        x = 0
        for image in images:
            pair.paste(image, (x, 0))
            x += image.width
        pair.save(OUT / f"{layout}-paired-top.png")
        print(layout, "rendered")


if __name__ == "__main__":
    main()
