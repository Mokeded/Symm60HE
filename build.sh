#!/bin/sh
# Rebuild only the current ribbon-PCB, plate, Fusion and firmware artifacts.
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
# Combined panel PCB/schematic/project files are now the authoritative
# electrical designs.  Do not regenerate them from the retained half-board
# migration inputs during an ordinary manufacturing build.
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
run_freecad_script() {
    FREECAD_SCRIPT=$1
    export FREECAD_SCRIPT
    # FreeCAD 1.1 no longer treats a bare .py argument as an executable macro.
    # Feed an explicit compile/exec command to its console so __file__ and
    # __name__ retain normal script semantics on both old and new releases.
    printf '%s\n' \
        "import os; p=os.environ['FREECAD_SCRIPT']; exec(compile(open(p).read(), p, 'exec'), {'__file__': p, '__name__': '__main__'})" \
        'exit()' | "$FREECADCMD" -c
}
run_freecad_script cad/export_fusion_reference.py
run_freecad_script cad/verify_fusion_reference.py
"$PYTHON" releases/release.py
"$PYTHON" releases/release_layout_pcbs.py
"$PYTHON" layouts/verify_layout_panels.py
"$PYTHON" verify.py

# Compile the current AT32F405 Symm60HE firmware and collect the distributable
# outputs in firmware/build.  PlatformIO is installed by requirements.txt.
PLATFORMIO=${PLATFORMIO:-$ROOT/.venv/bin/platformio}
if [ ! -x "$PLATFORMIO" ]; then
    PLATFORMIO=$(command -v platformio 2>/dev/null || true)
fi
if [ -z "$PLATFORMIO" ] || [ ! -x "$PLATFORMIO" ]; then
    echo "Missing PlatformIO. Install the project requirements first." >&2
    exit 2
fi
"$PLATFORMIO" run --project-dir "$ROOT/firmware/libhmk" -e symm60he
mkdir -p "$ROOT/firmware/build"
for artifact in firmware.bin firmware.elf firmware.hex; do
    artifact_source="$ROOT/firmware/libhmk/.pio/build/symm60he/$artifact"
    if [ -f "$artifact_source" ]; then
        cp "$artifact_source" "$ROOT/firmware/build/$artifact"
    fi
done
