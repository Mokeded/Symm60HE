# DOE 60% curvature, carrying the Symm60HE builds

Five KLE files. `doe60-reference.kle.json` is the DOE 60% itself; the four
`doe-*.kle.json` files are this project's builds — same key sets, same option
groups, same counts as the committed switch map — placed on the DOE's geometry
instead of the current reconstruction's.

Paste any of them into <https://www.keyboard-layout-editor.com> under
*Raw data*. They are plain KLE rows with no metadata header, which is also what
`tools/geom.py` parses.

## Where the geometry came from

The geekhack interest-check thread publishes no KLE link and no raw data, so
the layout was measured off the published KLE render:

- key faces segmented by colour, one minimum-area rectangle fitted per face;
- scale read from the render's own pitch, 1u = 54 px (a 1u face is 39 px, a 3u
  face 147 px, so `width_u = (face_px + 15) / 54`);
- fitted rotations land on whole multiples of 3° — 0, 3, 6, 9 across the four
  column groups, plus 5° on the bottom-row mod — so they are used as measured
  rather than smoothed.

Rows 1–4 are therefore the DOE's own centres and angles. **Row 5 is
constructed**: the DOE's bottom row is WKL-blocked exactly where these builds
fit keys, so it gives no reference for them. Each build's bottom row is instead
chained edge to edge along the same path the DOE's bottom row follows — two or
three keys at 0°, the 1.5u mod at 5°, the 2.25u space at 9°.

The right half is an exact mirror about the measured axis (u 7.4305). The
render is symmetric to within ~0.06u, and the boards are symmetric by design.

## How this differs from the committed switch map

Both describe the same 69 switch positions, 33 left and 36 right, with the same
16 mutually exclusive positions and the same per-build counts (60 / 59 / 63 /
62). Only the geometry moves:

| | `Symm60HE-switch-map.csv` | these files |
|---|---|---|
| Outer column rotation | 6.5° | **9°** |
| Column rotations, row 1 | 0 / 0 / 0 / 0.12 / 2.19 / 5.01 / 6.5 | **0 / 0 / 0 / 3 / 6 / 9 / 9** |
| Row-1 drop across the half | 0.20u | **0.46u** |
| Inner Y-to-Y gap | 24.0 mm | **42.3 mm** |
| Half extent (W × H) | 154.3 × 100.7 mm | 146.9 × 104.6 mm |

The current reconstruction is a flatter fan than the DOE it was measured from,
and the halves sit considerably closer together.

## Adopting them

Nothing here is wired into the build. `tools/geom.py` reads `layout/kle/` and
falls back to the committed switch map; this directory is not that path, so the
project still builds from the CSV until you say otherwise.

To rebuild the project on this geometry:

    cd tools
    SYMM60HE_KLE_DIR=../layout/kle-doe60 python3 geom.py   # rewrites the switch map

That regenerates `Symm60HE-switch-map.csv`, and every downstream artefact
follows from it: switch placement on both halves, the mux channel assignment,
all five plate pairs, the Fusion reference assembly, and the release sets. It
is a board change, not a drawing change — re-run `tools/verify.py` and re-route
before believing any of it.
