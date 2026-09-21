# DOE reference reconstruction

`doe-geekhack-reconstructed.kle.json` is a reverse-engineered KLE-compatible
description of the main key arrangement in the supplied 1176 x 477 Geekhack
image. It is evidence for the original key-field curvature, not original DOE
source data.

The image was calibrated at 54 pixels per key unit and 19.05 mm per key unit.
Near-white key-face regions were segmented, their convex hulls were fitted to
minimum-area rotated rectangles, and the recovered angles were rounded to the
clear KLE increments visible in the source: 0, +/-3, +/-6, and +/-9 degrees,
plus +/-5 degrees for the two bottom modifiers. Measured centres are retained
to six decimal KLE units (about 0.00002 mm numeric resolution); the meaningful
accuracy remains limited by rasterisation to approximately +/-0.2 mm and
approximately +/-0.25 degrees.

Every key is represented as an independent KLE row so that `r`, `rx`, and `ry`
can encode its measured absolute centre without guessing the unpublished
rotation pivots. Keyboard Layout Editor accepts this representation even
though it is less convenient to hand-edit than the designer's likely source.

This file deliberately lives under `layout/reference`, not `layout/kle`, so a
reference-only 3u-spacebar layout can never silently replace the project's
universal bottom-row options. The reviewed tilted centres and angles have been
propagated into `Symm60HE-switch-map.csv` by
`tools/apply_doe_reference_tilt.py`; that migration preserves the straight
clusters and adapts the recovered bottom curve to the universal 2.25u
spacebars.
