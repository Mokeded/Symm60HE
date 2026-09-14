#!/usr/bin/env python3
"""Draw how the seated Mill-Max 854/856 pair actually mates.

Sections and plan views are traced from the generated meshes of
``Symm60HE-case-reference-assembly``; every dimension comes from
``pogo_mate_geometry``. Run after regenerating the reference assembly.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Rectangle

from pogo_mate_geometry import (SPRING, TARGET, densify, load_stl, mating_frame,
                                measure, pillar_diameter)

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "docs/img"

PCB_THICKNESS = 1.2
APERTURE_FLOAT = 0.4          # per-side X/Y clearance of the kernel aperture

SPRING_COLOUR = "#b8860b"
TARGET_COLOUR = "#1f6f8b"
PCB_COLOUR = "#14532d"
DIM = "#8a1c1c"


def local_clouds():
    spring_raw = load_stl(SPRING)
    target_raw = load_stl(TARGET)
    rot, centre = mating_frame(spring_raw)

    def to_local(tris):
        return ((tris.reshape(-1, 3) - centre) @ rot.T).reshape(-1, 3, 3)

    return densify(to_local(spring_raw)), densify(to_local(target_raw))


def section(points, half_band=0.03):
    """Points inside a thin slab through the contact row, as (length, mate)."""
    picked = points[np.abs(points[:, 1]) < half_band]
    return picked[:, 0], picked[:, 2]


def dim_line(ax, x, y0, y1, text, side=1, colour=DIM, pad=0.06, fontsize=8):
    ax.annotate("", xy=(x, y0), xytext=(x, y1),
                arrowprops=dict(arrowstyle="<->", color=colour, lw=1.0))
    ax.text(x + side * pad, (y0 + y1) / 2, text, color=colour, fontsize=fontsize,
            ha="left" if side > 0 else "right", va="center")


def boards(ax, geo, x0, x1):
    ax.add_patch(Rectangle((x0, geo.spring_seat - PCB_THICKNESS), x1 - x0,
                           PCB_THICKNESS, facecolor=PCB_COLOUR, alpha=0.85, zorder=0))
    ax.text(x0 + 0.15, geo.spring_seat - PCB_THICKNESS / 2,
            "spring module PCB, 1.2 mm", color="white", fontsize=7, va="center")
    ax.add_patch(Rectangle((x0, geo.target_seat), x1 - x0, PCB_THICKNESS,
                           facecolor=PCB_COLOUR, alpha=0.85, zorder=0))
    ax.text(x0 + 0.15, geo.target_seat + PCB_THICKNESS / 2,
            "Hall PCB, 1.2 mm", color="white", fontsize=7, va="center")


def figure_section(geo, spring, target, path):
    sx, sz = section(spring)
    tx, tz = section(target)
    fig, ax = plt.subplots(figsize=(13, 6.2))
    x0, x1 = -8.6, 8.6
    boards(ax, geo, x0, x1)
    ax.scatter(sx, sz, s=0.05, c=SPRING_COLOUR, linewidths=0, zorder=3)
    ax.scatter(tx, tz, s=0.05, c=TARGET_COLOUR, linewidths=0, zorder=3)

    for level, label in [(geo.spring_seat, "854 seats here"),
                         (geo.target_seat, "856 seats here")]:
        ax.axhline(level, color="#999999", lw=0.6, ls=(0, (6, 4)), zorder=1)
    ax.axhline(geo.plunger_tip, color=DIM, lw=0.7, ls=(0, (2, 3)), zorder=1)
    ax.text(x1 - 0.1, geo.plunger_tip + 0.07, "contact plane", color=DIM,
            fontsize=8, ha="right")

    dim_line(ax, 8.15, geo.spring_seat, geo.target_seat,
             f"board-to-board\n{geo.board_to_board:.3f} mm", side=1)
    dim_line(ax, -8.15, geo.spring_housing_face, geo.target_housing_face,
             f"housing gap\n{geo.housing_gap:.3f} mm", side=-1)

    ax.set_xlim(x0, x1 + 1.9)
    ax.set_ylim(geo.spring_seat - PCB_THICKNESS - 0.5, geo.target_seat + PCB_THICKNESS + 0.5)
    ax.set_aspect("equal")
    ax.set_xlabel("along the contact row (mm)")
    ax.set_ylabel("mating axis (mm)")
    ax.set_title("Mill-Max 854 spring / 856 target, seated pose\n"
                 f"12 contacts on 1.27 mm pitch, preload {geo.preload:.4f} mm, "
                 f"{1.016 - geo.preload:.4f} mm of the 1.016 mm stroke left",
                 fontsize=11)
    ax.grid(alpha=0.15, lw=0.5)
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)


def trace_profile(points, low, high, step=0.004):
    """Outside diameter of one contact feature, sampled along the mating axis."""
    out = []
    for height in np.arange(low, high + 1e-9, step):
        diameter = pillar_diameter(points, float(height))
        if diameter == diameter and diameter < 2.0:
            out.append((float(height), diameter))
    return out


def smooth(profile, window=3):
    """Drop tessellation dropouts so the traced outline reads cleanly."""
    heights = [z for z, _ in profile]
    widths = [d for _, d in profile]
    out = []
    for i, z in enumerate(heights):
        lo = max(0, i - window)
        hi = min(len(widths), i + window + 1)
        out.append((z, max(widths[lo:hi])))
    return out


def taper_extent(profile, full_diameter, tolerance=0.004):
    """Height over which the target pillar tapers to its contact flat."""
    ordered = sorted(profile)
    base = ordered[0][0]
    for z, d in ordered:
        if d >= full_diameter - tolerance:
            return base, z
    return base, ordered[-1][0]


def half_outline(profile):
    """Closed polygon for one contact, mirrored about its axis."""
    right = [(d / 2, z) for z, d in profile]
    left = [(-d / 2, z) for z, d in reversed(profile)]
    return np.array(right + left)


def figure_contact(geo, spring, target, path):
    spring_profile = smooth(trace_profile(spring, geo.spring_housing_face + 0.006,
                                          geo.plunger_tip - 0.001))
    target_profile = smooth(trace_profile(target, geo.target_contact + 0.001,
                                          geo.target_housing_face - 0.006))
    taper_low, taper_top = taper_extent(target_profile, geo.target_pillar_diameter)
    fig, ax = plt.subplots(figsize=(10.2, 8.8))

    ax.add_patch(plt.Polygon(half_outline(spring_profile), closed=True,
                             facecolor=SPRING_COLOUR, alpha=0.65,
                             edgecolor=SPRING_COLOUR, lw=1.4, zorder=3))
    ax.add_patch(plt.Polygon(half_outline(target_profile), closed=True,
                             facecolor=TARGET_COLOUR, alpha=0.55,
                             edgecolor=TARGET_COLOUR, lw=1.4, zorder=3))
    ax.add_patch(Rectangle((-1.02, geo.spring_housing_face - 0.30), 2.04, 0.30,
                           facecolor=SPRING_COLOUR, alpha=0.30,
                           edgecolor=SPRING_COLOUR, lw=1.0, zorder=2))
    ax.add_patch(Rectangle((-1.02, geo.target_housing_face), 2.04, 0.30,
                           facecolor=TARGET_COLOUR, alpha=0.25,
                           edgecolor=TARGET_COLOUR, lw=1.0, zorder=2))
    ax.text(-0.99, geo.spring_housing_face - 0.15, "854 body", fontsize=8.5,
            color=SPRING_COLOUR, va="center")
    ax.text(-0.99, geo.target_housing_face + 0.15, "856 body", fontsize=8.5,
            color=TARGET_COLOUR, va="center")

    ax.axhline(geo.plunger_tip, color=DIM, lw=0.8, ls=(0, (3, 3)), zorder=1)
    ax.text(0.99, geo.plunger_tip + 0.012, "contact plane", fontsize=8.5,
            color=DIM, ha="right")

    dim_line(ax, -0.72, geo.spring_housing_face, geo.plunger_tip,
             f"plunger stands\n{geo.plunger_proud:.3f} proud\n"
             f"({geo.plunger_proud + geo.preload:.3f} free)", side=-1, pad=0.03)
    dim_line(ax, 0.72, geo.target_contact, geo.target_housing_face,
             f"pillar stands\n{geo.pillar_proud:.3f} proud", side=1, pad=0.03)
    dim_line(ax, 0.46, geo.spring_housing_face, geo.target_housing_face,
             f"{geo.housing_gap:.3f} air\nbetween bodies", side=1, pad=0.03)

    ax.annotate(f"the only lead-in there is:\n"
                f"\u00f8{geo.target_pillar_diameter:.3f} \u2192 "
                f"\u00f8{geo.target_flat_diameter:.3f} over "
                f"{taper_top - taper_low:.3f} mm",
                xy=(geo.target_pillar_diameter / 2 - 0.01, (taper_top + taper_low) / 2),
                xytext=(-0.98, geo.target_housing_face - 0.10), fontsize=8.5,
                color=TARGET_COLOUR,
                arrowprops=dict(arrowstyle="->", color=TARGET_COLOUR, lw=0.9))
    ax.annotate(f"plunger \u00f8{geo.plunger_diameter:.3f}",
                xy=(geo.plunger_diameter / 2, geo.plunger_tip - 0.06),
                xytext=(0.24, geo.spring_barrel_top - 0.07), fontsize=8.5,
                color=SPRING_COLOUR,
                arrowprops=dict(arrowstyle="->", color=SPRING_COLOUR, lw=0.9))
    ax.annotate(f"barrel \u00f8{0.9395:.3f}",
                xy=(0.9395 / 2, (geo.spring_housing_face + geo.spring_barrel_top) / 2),
                xytext=(0.60, geo.spring_housing_face - 0.10), fontsize=8.5,
                color=SPRING_COLOUR,
                arrowprops=dict(arrowstyle="->", color=SPRING_COLOUR, lw=0.9))

    ax.set_xlim(-1.02, 1.02)
    ax.set_ylim(geo.spring_housing_face - 0.32, geo.target_housing_face + 0.32)
    ax.set_aspect("equal")
    ax.set_xlabel("across the contact (mm)")
    ax.set_ylabel("mating axis (mm)")
    ax.set_title("One contact, seated, traced from the vendor STEP\n"
                 f"a flat butt joint with a {taper_top - taper_low:.3f} mm chamfer, "
                 "not a funnel", fontsize=11)
    ax.grid(alpha=0.15, lw=0.5)
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)


def figure_landing(geo, path):
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 6.4))
    plunger_r = geo.plunger_diameter / 2
    pillar_r = geo.target_pillar_diameter / 2

    ax = axes[0]
    ax.add_patch(Circle((0, 0), pillar_r, facecolor=TARGET_COLOUR, alpha=0.30,
                        edgecolor=TARGET_COLOUR, lw=1.4))
    ax.add_patch(Circle((0, 0), geo.target_flat_diameter / 2, facecolor="none",
                        edgecolor=TARGET_COLOUR, lw=0.9, ls=(0, (3, 3))))
    ax.add_patch(Circle((0, 0), plunger_r, facecolor=SPRING_COLOUR, alpha=0.55,
                        edgecolor=SPRING_COLOUR, lw=1.4))
    ax.add_patch(Circle((0, 0), geo.landing_budget, facecolor="none",
                        edgecolor=DIM, lw=1.6))
    ax.annotate(f"usable slip before the tip\nleaves the pillar: "
                f"{geo.landing_budget:.3f} mm radial",
                xy=(geo.landing_budget * 0.7, geo.landing_budget * 0.7),
                xytext=(0.30, 0.46), fontsize=9, color=DIM,
                arrowprops=dict(arrowstyle="->", color=DIM, lw=1.0))
    ax.text(0, -pillar_r - 0.09,
            f"856 pillar ø{geo.target_pillar_diameter:.3f}   "
            f"flat ø{geo.target_flat_diameter:.3f}   "
            f"plunger ø{geo.plunger_diameter:.3f}",
            ha="center", fontsize=8.5)
    ax.set_xlim(-0.62, 0.62)
    ax.set_ylim(-0.62, 0.62)
    ax.set_title("What one contact can absorb", fontsize=11)

    ax = axes[1]
    ax.add_patch(Circle((0, 0), geo.landing_budget, facecolor=DIM, alpha=0.30,
                        edgecolor=DIM, lw=1.6))
    ax.add_patch(Rectangle((-APERTURE_FLOAT, -APERTURE_FLOAT), 2 * APERTURE_FLOAT,
                           2 * APERTURE_FLOAT, facecolor="none", edgecolor="#444444",
                           lw=1.6, ls=(0, (5, 4))))
    ax.text(0, geo.landing_budget + 0.04,
            f"contact budget ±{geo.landing_budget:.3f}", ha="center",
            fontsize=9, color=DIM)
    ax.text(0, APERTURE_FLOAT + 0.04,
            f"kernel aperture float ±{APERTURE_FLOAT:.2f} per side",
            ha="center", fontsize=9, color="#444444")
    ax.text(0, -APERTURE_FLOAT - 0.13,
            f"the aperture lets the module wander "
            f"{APERTURE_FLOAT / geo.landing_budget:.1f}× further\n"
            "than the contact can follow", ha="center", fontsize=9)
    ax.set_xlim(-0.62, 0.62)
    ax.set_ylim(-0.62, 0.62)
    ax.set_title("...against how far the module is allowed to float", fontsize=11)

    for ax in axes:
        ax.set_aspect("equal")
        ax.grid(alpha=0.2, lw=0.5)
        ax.set_xlabel("mm")
        ax.set_ylabel("mm")
    fig.suptitle("Landing zone: the 854/856 pair does not self-align", fontsize=12)
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)


def main():
    geo = measure()
    spring, target = local_clouds()
    IMG.mkdir(parents=True, exist_ok=True)
    figure_section(geo, spring, target, IMG / "37-pogo-mate-section.png")
    figure_contact(geo, spring, target, IMG / "38-pogo-mate-contact-detail.png")
    figure_landing(geo, IMG / "39-pogo-mate-landing-zone.png")
    print("wrote 37/38/39 to", IMG)


if __name__ == "__main__":
    main()
