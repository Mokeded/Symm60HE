#!/usr/bin/env python3
"""Draw the magnetic-pogo spring module, both layers, from the board file."""
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_mag_pogo import MODULE_H, MODULE_W, OUT  # noqa: E402
from sexp import find, first, loads  # noqa: E402
from verify_mag_pogo import geometry  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "docs/img"
COLOUR = {"F.Cu": "#c0392b", "B.Cu": "#2471a3"}


def draw(ax, name, layer):
    board = loads((OUT / f"{name}.kicad_pcb").read_text())
    pads, copper = geometry(board)
    ax.add_patch(plt.Rectangle((0, 0), MODULE_W, MODULE_H, facecolor="#f2efe6",
                               edgecolor="#555555", lw=1.2, zorder=0))
    for geom, net, layers, _ in copper:
        if layer not in layers:
            continue
        xs, ys = geom.exterior.xy
        ax.fill(xs, ys, color=COLOUR[layer], alpha=0.55, lw=0, zorder=2)
    for pad in pads:
        if layer not in pad["lays"]:
            continue
        xs, ys = pad["g"].exterior.xy
        ax.fill(xs, ys, color="#b7950b", alpha=0.95, lw=0, zorder=3)
    for text in find(board, "gr_text"):
        at = first(text, "at")
        ax.text(float(at[1]), float(at[2]), text[1], fontsize=6,
                ha="center", va="center", color="#333333", zorder=4)
    ax.set_xlim(-1, MODULE_W + 1)
    ax.set_ylim(MODULE_H + 1, -1)
    ax.set_aspect("equal")
    ax.set_title(f"{name.replace('Symm60HE-Mag-', '')}  {layer}", fontsize=10)
    ax.set_xlabel("mm", fontsize=8)
    ax.tick_params(labelsize=7)


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    for row, name in enumerate(("Symm60HE-Mag-Left-SpringModule",
                                "Symm60HE-Mag-Right-SpringModule")):
        for col, layer in enumerate(("F.Cu", "B.Cu")):
            draw(axes[row][col], name, layer)
    fig.suptitle("Magnetic-pogo spring modules, 32 x 18 mm\n"
                 "F.Cu carries the 12 contacts and the ground bus; "
                 "B.Cu carries the ZIF and the signal fan", fontsize=12)
    fig.tight_layout()
    path = IMG / "42-mag-pogo-spring-modules.png"
    fig.savefig(path, dpi=170)
    print("wrote", path.relative_to(ROOT))


if __name__ == "__main__":
    main()
