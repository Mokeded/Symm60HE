#!/bin/sh
# Rebuild manufacturing and Fusion handoff artifacts from the routed sources.
set -eu
cd "$(dirname "$0")/tools"
PYTHON=${PYTHON:-../.venv/bin/python}
if [ ! -x "$PYTHON" ]; then
    echo "Missing project Python environment: $PYTHON" >&2
    echo "Create it with: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
    exit 2
fi
"$PYTHON" lock_ffc_connector.py
"$PYTHON" orient_daughter_ffc_outward.py
"$PYTHON" add_daughterboard_fiducials.py
"$PYTHON" reduce_daughterboard_vias.py
"$PYTHON" apply_shared_midpoints.py
"$PYTHON" panelize.py
"$PYTHON" mkplate.py
"$PYTHON" make_neo_pogo.py
"$PYTHON" prepare_fusion_reference.py
FREECADCMD=${FREECADCMD:-/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd}
if [ ! -x "$FREECADCMD" ]; then
    echo "Missing FreeCAD command line tool: $FREECADCMD" >&2
    exit 2
fi
"$FREECADCMD" export_fusion_reference.py
"$FREECADCMD" export_pogo16_mechanics.py
"$FREECADCMD" export_tenting_solution.py
"$FREECADCMD" verify_tenting_solution.py
"$FREECADCMD" export_neo_fusion_reference.py
"$FREECADCMD" export_neo_mounting_reference.py
"$PYTHON" render_fusion_reference.py
"$PYTHON" release.py
"$PYTHON" verify.py
"$PYTHON" make_pogo16_coupon.py
"$PYTHON" release_pogo16.py
"$PYTHON" render_pogo16.py
"$PYTHON" render_tenting_solution.py
"$PYTHON" verify_neo_pogo.py
"$PYTHON" release_neo_pogo.py
"$PYTHON" release_pcbway_neo_pogo.py
"$PYTHON" render_neo_pogo.py
"$PYTHON" render_neo_mounting_reference.py
"$PYTHON" render_current_pcbs.py
"$PYTHON" render_gallery.py
