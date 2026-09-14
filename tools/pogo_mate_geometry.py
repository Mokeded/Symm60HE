#!/usr/bin/env python3
"""Measure the seated Mill-Max 854/856 mate from the case reference assembly.

Everything here is read off the generated meshes of
``Symm60HE-case-reference-assembly`` -- no dimension is retyped from the
datasheet -- so the numbers track the assembly if it is regenerated.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
GEN = ROOT / "case/fusion360/generated"

SPRING = GEN / "CaseRef-LeftSpringConnector.stl"
TARGET = GEN / "CaseRef-LeftTargetConnector.stl"

# Mill-Max published figures, used only to cross-check what we measure.
# FREE_HEIGHT_854 is the whole part including the tails that pass through the
# 1.2 mm module PCB, which is what the vendor STEP spans when uncompressed.
FREE_HEIGHT_854 = 4.2164
FULL_STROKE_854 = 1.016


def load_stl(path: Path) -> np.ndarray:
    """Return an (n, 3, 3) array of triangle vertices from a binary STL."""
    with path.open("rb") as handle:
        handle.read(80)
        count = struct.unpack("<I", handle.read(4))[0]
        raw = np.frombuffer(handle.read(count * 50), dtype=np.uint8).reshape(count, 50)
    return raw[:, 12:48].copy().view("<f4").reshape(count, 3, 3).astype(np.float64)


def mating_frame(spring: np.ndarray):
    """Build a frame with X along the contact row, Z along the mating axis."""
    pts = spring.reshape(-1, 3)
    centre = pts.mean(axis=0)
    _, _, axes = np.linalg.svd(pts - centre, full_matrices=False)
    length = axes[0]
    mate = axes[int(np.argmax(np.abs(axes[:, 2])))]
    if mate[2] < 0:
        mate = -mate
    if length[1] < 0:
        length = -length
    width = np.cross(mate, length)
    width /= np.linalg.norm(width)
    return np.vstack([length, width, mate]), centre


def horizontal_planes(tris: np.ndarray, min_area: float = 0.15):
    """Significant planes normal to the mating axis, as (height, area, facing)."""
    normals = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    norms = np.linalg.norm(normals, axis=1)
    areas = norms / 2
    flat = np.abs(normals[:, 2]) / (norms + 1e-12) > 0.999
    heights = np.round(tris[flat][:, :, 2].mean(axis=1), 3)
    found = []
    for level in np.unique(heights):
        picked = heights == level
        area = areas[flat][picked].sum()
        if area >= min_area:
            facing = "up" if normals[flat][picked][:, 2].mean() > 0 else "down"
            found.append((float(level), float(area), facing))
    return found


def merge_levels(planes, tolerance=0.002):
    """Collapse mesh-quantised levels that are really one face."""
    merged = []
    for height, area, facing in sorted(planes):
        if merged and facing == merged[-1][2] and height - merged[-1][0] <= tolerance:
            total = merged[-1][1] + area
            blend = (merged[-1][0] * merged[-1][1] + height * area) / total
            merged[-1] = (blend, total, facing)
        else:
            merged.append((height, area, facing))
    return merged


def contact_diameter(tris: np.ndarray, height: float, positions: int = 12,
                     band: float = 0.003, width_limit: float = 0.55) -> float:
    """Equivalent circular diameter of one contact face at ``height``."""
    normals = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    norms = np.linalg.norm(normals, axis=1)
    flat = np.abs(normals[:, 2]) / (norms + 1e-12) > 0.999
    z = tris[:, :, 2].mean(axis=1)
    w = tris[:, :, 1].mean(axis=1)
    picked = flat & (np.abs(z - height) < band) & (np.abs(w) < width_limit)
    area = (norms[picked] / 2).sum() / positions
    return 2 * float(np.sqrt(area / np.pi))


def pillar_diameter(points: np.ndarray, height: float, band: float = 0.006,
                    width_limit: float = 0.55) -> float:
    """Outside diameter of the contact pillars sliced at ``height``."""
    picked = points[(np.abs(points[:, 2] - height) < band)
                    & (np.abs(points[:, 1]) < width_limit)]
    if len(picked) < 50:
        return float("nan")
    order = np.argsort(picked[:, 0])
    splits = np.where(np.diff(picked[order][:, 0]) > 0.25)[0]
    spans = [picked[order][group][:, 0].ptp() if hasattr(np.ndarray, "ptp")
             else picked[order][group][:, 0].max() - picked[order][group][:, 0].min()
             for group in np.split(np.arange(len(picked)), splits + 1)
             if len(group) >= 30]
    return float(np.mean(spans)) if spans else float("nan")


def densify(tris: np.ndarray, divisions: int = 14) -> np.ndarray:
    """Scatter points across each facet so thin slices stay well sampled."""
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    samples = []
    for i in range(divisions + 1):
        for j in range(divisions + 1 - i):
            u, v = i / divisions, j / divisions
            samples.append(a * (1 - u - v) + b * u + c * v)
    return np.concatenate(samples, axis=0)


@dataclass
class MateGeometry:
    spring_tail: float          # bottom of the 854 through-board tails
    spring_seat: float          # 854 seating face -> module PCB top
    spring_housing_face: float  # top of the 854 body
    spring_barrel_top: float
    plunger_tip: float
    target_contact: float       # lowest face of the 856 contact pillars
    target_housing_face: float
    target_seat: float          # 856 seating face -> Hall PCB underside
    plunger_diameter: float
    target_flat_diameter: float
    target_pillar_diameter: float

    @property
    def board_to_board(self):
        return self.target_seat - self.spring_seat

    @property
    def preload(self):
        return FREE_HEIGHT_854 - (self.plunger_tip - self.spring_tail)

    @property
    def housing_gap(self):
        return self.target_housing_face - self.spring_housing_face

    @property
    def plunger_proud(self):
        return self.plunger_tip - self.spring_housing_face

    @property
    def pillar_proud(self):
        return self.target_housing_face - self.target_contact

    @property
    def landing_budget(self):
        """Radial misalignment before the tip runs off the target pillar."""
        return (self.target_pillar_diameter - self.plunger_diameter) / 2


def measure() -> MateGeometry:
    spring_raw = load_stl(SPRING)
    target_raw = load_stl(TARGET)
    rot, centre = mating_frame(spring_raw)

    def to_local(tris):
        return ((tris.reshape(-1, 3) - centre) @ rot.T).reshape(-1, 3, 3)

    spring = to_local(spring_raw)
    target = to_local(target_raw)

    spring_planes = merge_levels(horizontal_planes(spring))
    target_planes = merge_levels(horizontal_planes(target))

    spring_total = spring.reshape(-1, 3)[:, 2]
    target_total = target.reshape(-1, 3)[:, 2]

    # 854: seating face is the largest down-facing plane above the through-board
    # tails; the housing face is the largest up-facing plane below the tips.
    seat = max((p for p in spring_planes if p[2] == "down"), key=lambda p: p[1])[0]
    tip = float(spring_total.max())
    housing_face = max((p for p in spring_planes if p[2] == "up" and p[0] < tip - 0.05),
                       key=lambda p: p[1])[0]
    barrel_top = max(p[0] for p in spring_planes if p[2] == "up" and p[0] < tip - 0.05
                     and p[0] > housing_face)

    # 856: contact pillars are its lowest faces. Its seating face is the largest
    # down-facing plane above the housing face; anything higher is the tails that
    # pass up through the Hall PCB.
    contact = float(target_total.min())
    target_face = min((p for p in target_planes if p[2] == "down" and p[1] >= 5.0
                       and p[0] > contact + 0.05), key=lambda p: p[0])[0]
    # The seating face points up into the Hall PCB; the small plane above it is
    # the solder feature standing proud of that face, not the board line.
    target_seat = min((p for p in target_planes if p[2] == "up" and p[1] >= 5.0
                       and p[0] > target_face + 0.05), key=lambda p: p[0])[0]

    dense_target = densify(target)
    return MateGeometry(
        spring_tail=float(spring_total.min()),
        spring_seat=seat,
        spring_housing_face=housing_face,
        spring_barrel_top=barrel_top,
        plunger_tip=tip,
        target_contact=contact,
        target_housing_face=target_face,
        target_seat=target_seat,
        plunger_diameter=contact_diameter(spring, tip - 0.0003),
        target_flat_diameter=contact_diameter(target, contact + 0.0003),
        target_pillar_diameter=pillar_diameter(dense_target, contact + 0.18),
    )


def report(geo: MateGeometry) -> str:
    seated_height = geo.plunger_tip - geo.spring_tail
    preload = geo.preload
    lines = [
        "Seated Mill-Max 854/856 mate, measured from the case reference assembly",
        "",
        f"  module PCB top face (854 seat)   {geo.spring_seat:+8.4f}",
        f"  854 housing face                 {geo.spring_housing_face:+8.4f}",
        f"  854 barrel top                   {geo.spring_barrel_top:+8.4f}",
        f"  plunger tip / contact plane      {geo.plunger_tip:+8.4f}",
        f"  856 contact pillar face          {geo.target_contact:+8.4f}",
        f"  856 housing face                 {geo.target_housing_face:+8.4f}",
        f"  Hall PCB underside (856 seat)    {geo.target_seat:+8.4f}",
        "",
        f"  board-to-board                   {geo.board_to_board:8.4f} mm",
        f"  854 seated height, tail to tip   {seated_height:8.4f} mm"
        f"  (free {FREE_HEIGHT_854:.4f})",
        f"  preload                          {preload:8.4f} mm",
        f"  travel remaining                 {FULL_STROKE_854 - preload:8.4f} mm"
        f"  of {FULL_STROKE_854:.3f}",
        f"  housing face to housing face     {geo.housing_gap:8.4f} mm",
        f"  plunger proud of 854 housing     {geo.plunger_proud:8.4f} mm"
        f"  (free {geo.plunger_proud + preload:.4f})",
        f"  pillar proud of 856 housing      {geo.pillar_proud:8.4f} mm",
        "",
        f"  plunger tip diameter             {geo.plunger_diameter:8.4f} mm",
        f"  856 contact flat diameter        {geo.target_flat_diameter:8.4f} mm",
        f"  856 pillar outside diameter      {geo.target_pillar_diameter:8.4f} mm",
        f"  radial landing budget            {geo.landing_budget:8.4f} mm",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print(report(measure()))
