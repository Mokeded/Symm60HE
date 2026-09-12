"""Symm60HE case-design project setup for Fusion 360.

Builds a fresh Fusion design around the generated reference bodies under
case/fusion360, so case work can start immediately:

  Symm60HE Case                      (root, mm)
  +-- Reference (do not edit)        one component per placed STEP body
  |   +-- PCBs / Plates / Switches / Keycaps
  +-- Pogo references (optional)     hidden by default, see flags below
  +-- Case                           empty components to design in
      +-- Left top / Left bottom / Right top / Right bottom / Controller housing

Run it from Fusion: UTILITIES > ADD-INS > Scripts and Add-Ins (Shift+S),
select "Symm60HECaseSetup", Run. The script never modifies the STEP files.
"""

import os
import traceback

import adsk.core
import adsk.fusion

# --- configuration --------------------------------------------------------

# Folder that holds Symm60HE-reference-assembly.step and the individual
# Symm60HE-*.step files. Edit if the repository moves.
REFERENCE_DIR = r"E:\Symm60HE-GitHub-Upload\Symm60HE\case\fusion360"

# Name for the Fusion design; it is saved into a folder of the same name
# inside the currently active Fusion project.
DESIGN_NAME = "Symm60HE Case"

# Optional pogo-variant references. They import into a hidden component so
# the default view stays the checked FFC production candidate.
INCLUDE_NEO_POGO_REFERENCE = True       # pogo-neo/ full 35-body assembly
INCLUDE_NEO_MOUNTING_REFERENCE = True   # pogo-neo-mounting-reference/ carrier
INCLUDE_TENTING_SOLUTION = False        # tenting-solution/ fixed-tent module

# Save automatically at the end (needs Fusion to be signed in).
SAVE_DESIGN = True

# (group, component name, file relative to REFERENCE_DIR, opacity)
REFERENCE_BODIES = [
    ("PCBs", "Left PCB", "Symm60HE-LeftPCB.step", 1.0),
    ("PCBs", "Right PCB", "Symm60HE-RightPCB.step", 1.0),
    ("PCBs", "Daughterboard PCB", "Symm60HE-DaughterboardPCB.step", 1.0),
    ("Plates", "Left universal plate", "Symm60HE-LeftPlate.step", 1.0),
    ("Plates", "Right universal plate", "Symm60HE-RightPlate.step", 1.0),
    ("Switches", "Left switches", "Symm60HE-LeftSwitches.step", 0.5),
    ("Switches", "Right switches", "Symm60HE-RightSwitches.step", 0.5),
    ("Keycaps", "Left keycaps", "Symm60HE-LeftKeycaps.step", 0.35),
    ("Keycaps", "Right keycaps", "Symm60HE-RightKeycaps.step", 0.35),
]

OPTIONAL_REFERENCES = [
    (INCLUDE_NEO_POGO_REFERENCE, "Neo pogo reference (35 bodies)",
     os.path.join("pogo-neo", "Symm60HE-Neo-Pogo-Reference.step")),
    (INCLUDE_NEO_MOUNTING_REFERENCE, "Neo pogo mounting reference",
     os.path.join("pogo-neo-mounting-reference",
                  "Symm60HE-Neo-Pogo-Mounting-Reference.step")),
    (INCLUDE_TENTING_SOLUTION, "Fixed-tent pogo module",
     os.path.join("tenting-solution", "Symm60HE-fixed-tent-pogo-module.step")),
]

CASE_COMPONENTS = ["Left top", "Left bottom", "Right top", "Right bottom",
                   "Controller housing"]

# --- helpers --------------------------------------------------------------


def resolve_reference_dir():
    """Prefer the configured path; fall back to a copy living in the repo."""
    candidates = [REFERENCE_DIR]
    here = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.abspath(os.path.join(here, "..", "..")))
    for path in candidates:
        if os.path.isfile(os.path.join(path, "Symm60HE-reference-assembly.step")):
            return path
    raise RuntimeError(
        "Cannot find Symm60HE-reference-assembly.step. Set REFERENCE_DIR at the "
        "top of the script to the repository's case/fusion360 folder.")


def new_child(parent, name):
    occ = parent.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occ.component.name = name
    return occ


def import_step(app, parent_occ, path, name, opacity=1.0):
    """Import one STEP into parent and return the new occurrence."""
    target = parent_occ.component
    before = target.occurrences.count
    options = app.importManager.createSTEPImportOptions(path)
    options.isViewFit = False
    app.importManager.importToTarget(options, target)
    if target.occurrences.count <= before:
        raise RuntimeError(f"Fusion reported no new component for {path}")
    occ = target.occurrences.item(target.occurrences.count - 1)
    occ.component.name = name
    if opacity < 1.0:
        try:
            occ.component.opacity = opacity
        except Exception:
            pass
    try:
        occ.isGroundToParent = True
    except Exception:
        try:
            occ.isGrounded = True
        except Exception:
            pass
    return occ


# --- entry point ----------------------------------------------------------


def run(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    try:
        ref_dir = resolve_reference_dir()

        missing = [f for _, _, f, _ in REFERENCE_BODIES
                   if not os.path.isfile(os.path.join(ref_dir, f))]
        missing += [f for flag, _, f in OPTIONAL_REFERENCES
                    if flag and not os.path.isfile(os.path.join(ref_dir, f))]
        if missing:
            ui.messageBox("Missing reference files under\n" + ref_dir + "\n\n"
                          + "\n".join(missing), "Symm60HE setup")
            return

        doc = app.documents.add(
            adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        design.fusionUnitsManager.distanceDisplayUnits = \
            adsk.fusion.DistanceUnits.MillimeterDistanceUnits
        root = design.rootComponent
        try:
            root.name = DESIGN_NAME
        except Exception:
            pass  # root name follows the document name on save

        # Reference bodies, grouped so whole banks can be hidden together.
        ref_occ = new_child(root, "Reference (do not edit)")
        groups = {}
        imported = []
        for group, name, filename, opacity in REFERENCE_BODIES:
            if group not in groups:
                groups[group] = new_child(ref_occ, group)
            import_step(app, groups[group], os.path.join(ref_dir, filename),
                        name, opacity)
            imported.append(name)
            adsk.doEvents()

        # Optional pogo subsystems, hidden by default.
        optional_names = []
        wanted = [(n, f) for flag, n, f in OPTIONAL_REFERENCES if flag]
        if wanted:
            pogo_occ = new_child(root, "Pogo references (optional)")
            for name, filename in wanted:
                import_step(app, pogo_occ, os.path.join(ref_dir, filename), name)
                optional_names.append(name)
                adsk.doEvents()
            pogo_occ.isLightBulbOn = False

        # Empty components for the actual case work.
        case_occ = new_child(root, "Case")
        for name in CASE_COMPONENTS:
            new_child(case_occ, name)
        case_occ.activate()

        app.activeViewport.fit()

        saved_to = "not saved (SAVE_DESIGN is False)"
        if SAVE_DESIGN:
            try:
                project = app.data.activeProject
                folder = None
                for i in range(project.rootFolder.dataFolders.count):
                    candidate = project.rootFolder.dataFolders.item(i)
                    if candidate.name == DESIGN_NAME:
                        folder = candidate
                        break
                if folder is None:
                    folder = project.rootFolder.dataFolders.add(DESIGN_NAME)
                doc.saveAs(DESIGN_NAME, folder,
                           "Case-design reference set generated from "
                           "case/fusion360 (6 deg tent, 11 deg typing angle, "
                           "doe-wkl populated).", "")
                saved_to = f"{project.name} / {DESIGN_NAME} / {DESIGN_NAME}"
            except Exception as exc:  # offline, no active project, etc.
                saved_to = f"NOT saved automatically ({exc}). Use File > Save."

        ui.messageBox(
            "Symm60HE case project is ready.\n\n"
            f"Reference bodies imported: {len(imported)}\n"
            f"Optional pogo references (hidden): {len(optional_names)}\n"
            f"Empty case components: {', '.join(CASE_COMPONENTS)}\n\n"
            f"Saved as: {saved_to}\n\n"
            "Model the case in the 'Case' components. Keep the reference "
            "components unedited so they can be replaced when the PCBs "
            "or plates are regenerated.",
            "Symm60HE setup")
    except Exception:
        if ui:
            ui.messageBox("Symm60HE setup failed:\n\n" + traceback.format_exc(),
                          "Symm60HE setup")
