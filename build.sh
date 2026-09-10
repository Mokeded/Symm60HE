#!/bin/sh
# Regenerate everything from the KLE geometry.  Order matters.
set -e
cd "$(dirname "$0")/tools"
python3 mkfp.py            # footprint library
python3 mkboards.py        # three boards
python3 route.py           # two-layer maze routing and the GND pours
python3 mkplate.py         # plate DXFs
python3 mkcase.py          # case OpenSCAD
python3 mkproj.py          # project files, channel map, ribbon pinout
python3 img_boards.py      # images
python3 img_plate_case.py
python3 verify.py          # all checks
