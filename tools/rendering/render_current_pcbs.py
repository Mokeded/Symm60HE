#!/usr/bin/env python3
"""Render the current source and Neo spring-module PCBs into the gallery."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from verify import find_kicad_cli  # noqa: E402

OUT = ROOT / "docs/gallery"
TARGETS = (
    (ROOT / "pcb/Symm60HE-Left.kicad_pcb", "pcb-left"),
    (ROOT / "pcb/Symm60HE-Right.kicad_pcb", "pcb-right"),
    (ROOT / "pcb/Symm60HE-Daughterboard.kicad_pcb", "pcb-daughterboard"),
    (ROOT / "pcb/variants/pogo-neo/Symm60HE-Neo-Left-SpringModule.kicad_pcb",
     "pogo-left-spring-module"),
    (ROOT / "pcb/variants/pogo-neo/Symm60HE-Neo-Right-SpringModule.kicad_pcb",
     "pogo-right-spring-module"),
)


def main():
    cli = find_kicad_cli()
    if not cli:
        raise RuntimeError("kicad-cli not found")
    OUT.mkdir(parents=True, exist_ok=True)
    for board, stem in TARGETS:
        for side in ("top", "bottom"):
            output = OUT / f"{stem}-{side}.png"
            subprocess.run([
                cli, "pcb", "render", "--side", side,
                "--width", "1800", "--height", "1100",
                "--quality", "high", "--background", "opaque",
                "--use-board-stackup-colors", "-o", str(output), str(board),
            ], check=True)
            print(output.relative_to(ROOT))


if __name__ == "__main__":
    main()
