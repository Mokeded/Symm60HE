#!/bin/sh
# Rebuild manufacturing and Fusion handoff artifacts from the routed sources.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
TOOLS="$ROOT/tools"
cd "$TOOLS"
PYTHON=${PYTHON:-$ROOT/.venv/bin/python}
export PYTHONPATH="$TOOLS${PYTHONPATH:+:$PYTHONPATH}"
if [ ! -x "$PYTHON" ]; then
    echo "Missing project Python environment: $PYTHON" >&2
    echo "Create it with: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
    exit 2
fi
"$PYTHON" pcb/lock_ffc_connector.py
"$PYTHON" pcb/orient_daughter_ffc_outward.py
"$PYTHON" pcb/remove_daughterboard_fiducials.py
"$PYTHON" pcb/reduce_daughterboard_vias.py
"$PYTHON" pcb/relocate_half_mounts.py
# A footprint takes its Edge.Cuts aperture with it when it moves; the copy of
# that aperture in each pour outline does not.  Re-sync them before pouring.
for board in ../pcb/Symm60HE-Left.kicad_pcb ../pcb/Symm60HE-Right.kicad_pcb; do
    "$PYTHON" pcb/resync_zone_apertures.py "$board" "$board"
done
# Back-side references and fabrication labels must plot readable from the
# physical back of the board before panelization and Gerber export.
for board in ../pcb/Symm60HE-Left.kicad_pcb \
             ../pcb/Symm60HE-Right.kicad_pcb \
             ../pcb/Symm60HE-Daughterboard.kicad_pcb; do
    "$PYTHON" pcb/mirror_back_text.py "$board" "$board"
done
# Every alternate switch position remains independently sensed on the universal
# PCB. Do not collapse close alternatives to shared midpoint sensors.
# The stacked panel is the one that gets ordered: it is the smaller of the two
# in both area (369.7 vs 375.7 cm2) and longest edge (227.8 vs 310.2 mm).  The
# side-by-side arrangement is kept beside it for anyone who would rather have
# the halves in their assembled orientation.
"$PYTHON" pcb/panelize.py
"$PYTHON" pcb/panelize.py --arrangement side-by-side
"$PYTHON" mkplate.py
"$PYTHON" cad/prepare_fusion_reference.py
# FreeCAD assembles the reference solids the step above exported.  Look for it
# where each platform puts it rather than assuming one; FREECADCMD overrides.
if [ -z "${FREECADCMD:-}" ]; then
    for candidate in         /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd         "/c/Program Files/FreeCAD "*/bin/FreeCADCmd.exe         "C:/Program Files/FreeCAD "*/bin/FreeCADCmd.exe         "$(command -v freecadcmd 2>/dev/null)"         "$(command -v FreeCADCmd 2>/dev/null)"; do
        if [ -x "$candidate" ]; then
            FREECADCMD=$candidate
            break
        fi
    done
fi
if [ -z "${FREECADCMD:-}" ] || [ ! -x "$FREECADCMD" ]; then
    echo "Missing FreeCAD command line tool. Install FreeCAD, or point" >&2
    echo "FREECADCMD at its freecadcmd/FreeCADCmd.exe." >&2
    exit 2
fi
"$FREECADCMD" cad/export_fusion_reference.py
"$FREECADCMD" cad/verify_fusion_reference.py
"$FREECADCMD" cad/export_pogo16_mechanics.py
"$FREECADCMD" cad/export_tenting_solution.py
"$FREECADCMD" cad/verify_tenting_solution.py
"$PYTHON" rendering/render_fusion_reference.py
"$PYTHON" releases/release.py
"$PYTHON" releases/release_layout_pcbs.py
"$PYTHON" verify.py
"$PYTHON" pogo/make_pogo16_coupon.py
"$PYTHON" releases/release_pogo16.py
"$PYTHON" rendering/render_pogo16.py
"$PYTHON" rendering/render_tenting_solution.py
"$PYTHON" rendering/render_current_pcbs.py
"$PYTHON" rendering/render_layout_variants.py
"$PYTHON" rendering/render_gallery.py
