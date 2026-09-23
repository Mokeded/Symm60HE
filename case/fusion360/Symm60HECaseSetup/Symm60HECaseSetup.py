"""Create a componentized Fusion case-design project for Symm60HE.

Every imported STEP is already in its checked global assembly position, so the
parts land where they belong without being moved by hand.  The plate, switches
and keycaps of each half are grouped together as one visual datum; each Hall
PCB, the controller daughterboard and the two ribbon cables stay separate, so
the enclosure can be designed around them individually.

Run it from Fusion's Scripts and Add-Ins dialog.  The reference files are read
from the repository's ``case/fusion360`` folder, which the script finds on its
own when it lives in that folder's ``Symm60HECaseSetup`` subdirectory; set
``SYMM60HE_REFERENCE_DIR`` or edit ``REFERENCE_DIR`` below if it is installed
somewhere else, such as Fusion's own API/Scripts directory.
"""
import os
import traceback

import adsk.core
import adsk.fusion

# Leave empty to search; set it to the repository's case/fusion360 folder when
# this script is installed outside the repository.
REFERENCE_DIR = ""
REFERENCE_FILE = "Symm60HE-reference-assembly.step"
DESIGN_NAME = "Symm60HE case reference"
CASE_COMPONENTS = ["Left top", "Left bottom", "Right top", "Right bottom",
                   "Centre blocker and controller housing"]

# Each group becomes one Fusion component holding positioned reference parts.
REFERENCE_GROUPS = (
    ("Left plate + switches + keycaps", (
        ("Symm60HE-LeftPlate.step", "Left plate"),
        ("Symm60HE-LeftSwitches.step", "Left switches"),
        ("Symm60HE-LeftKeycaps.step", "Left keycaps"),
    )),
    ("Right plate + switches + keycaps", (
        ("Symm60HE-RightPlate.step", "Right plate"),
        ("Symm60HE-RightSwitches.step", "Right switches"),
        ("Symm60HE-RightKeycaps.step", "Right keycaps"),
    )),
    ("Left Hall-effect PCB", (
        ("Symm60HE-LeftPCB.step", "Left 1.2 mm Hall PCB"),
        ("Symm60HE-LeftPCBComponents.step", "Left fitted components"),
    )),
    ("Right Hall-effect PCB", (
        ("Symm60HE-RightPCB.step", "Right 1.2 mm Hall PCB"),
        ("Symm60HE-RightPCBComponents.step", "Right fitted components"),
    )),
    ("Central controller daughterboard", (
        ("Symm60HE-DaughterboardPCB.step", "Controller PCB"),
        ("Symm60HE-DaughterboardPCBComponents.step",
         "Controller fitted components"),
    )),
)

# The ribbon runs are flexible: they show where the cable goes, not a solid the
# case has to clear, so they are grouped apart and start hidden.
CABLE_GROUP = ("Ribbon cable routes", (
    ("Symm60HE-LeftRibbonCable.step", "Left ribbon route"),
    ("Symm60HE-RightRibbonCable.step", "Right ribbon route"),
))


def resolve_reference_dir():
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.environ.get("SYMM60HE_REFERENCE_DIR", ""),
        REFERENCE_DIR,
        # Installed inside the repository, one level under case/fusion360.
        os.path.abspath(os.path.join(here, "..")),
        os.path.abspath(os.path.join(here, "..", "..")),
    ]
    for path in candidates:
        if path and os.path.isfile(os.path.join(path, REFERENCE_FILE)):
            return path
    raise RuntimeError(
        "Cannot find %s. Set SYMM60HE_REFERENCE_DIR, or REFERENCE_DIR at the "
        "top of this script, to the repository's case/fusion360 folder."
        % REFERENCE_FILE)


def new_child(parent, name):
    component = (parent.component if isinstance(parent, adsk.fusion.Occurrence)
                 else parent)
    occurrence = component.occurrences.addNewComponent(
        adsk.core.Matrix3D.create())
    occurrence.component.name = name
    return occurrence


def import_part(app, parent, path, name, ground=False):
    target = (parent.component if isinstance(parent, adsk.fusion.Occurrence)
              else parent)
    before = target.occurrences.count
    options = app.importManager.createSTEPImportOptions(path)
    options.isViewFit = False
    app.importManager.importToTarget(options, target)
    if target.occurrences.count <= before:
        raise RuntimeError("Fusion reported no imported occurrence for " + path)
    occurrence = target.occurrences.item(target.occurrences.count - 1)
    occurrence.component.name = name
    if ground:
        try:
            occurrence.isGroundToParent = True
        except Exception:
            try:
                occurrence.isGrounded = True
            except Exception:
                pass
    return occurrence


def import_group(app, parent, name, ref_dir, files, registry):
    """Create one user-facing component containing positioned reference parts."""
    group = new_child(parent, name)
    missing = [filename for filename, _ in files
               if not os.path.isfile(os.path.join(ref_dir, filename))]
    if missing:
        raise RuntimeError("Cannot find component STEP(s): " +
                           ", ".join(missing))
    for filename, part_name in files:
        occurrence = import_part(app, group, os.path.join(ref_dir, filename),
                                 part_name)
        key = filename[len("Symm60HE-"):-len(".step")]
        registry[key] = occurrence
    return group


def check_imports(registry):
    """Fail visibly if Fusion brought a component in with no geometry.

    A STEP that imports as an empty occurrence is the usual way this goes
    wrong, and it is easy to miss on screen behind the parts that did load.
    The assembled positions themselves come from the STEPs, which are exported
    already placed, so there is nothing here to re-derive: `reference-layout`
    in `generated/` records the flat board geometry they were built from.
    """
    problems = []
    for name, occurrence in sorted(registry.items()):
        try:
            box = occurrence.preciseBoundingBox
        except Exception:
            box = occurrence.boundingBox
        if box is None:
            problems.append(name + ": no geometry imported")
            continue
        size = max(box.maxPoint.x - box.minPoint.x,
                   box.maxPoint.y - box.minPoint.y,
                   box.maxPoint.z - box.minPoint.z)
        if size <= 0.0:
            problems.append(name + ": imported component is empty")
    if problems:
        raise RuntimeError("Import check failed:\n" + "\n".join(problems))


def run(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    try:
        ref_dir = resolve_reference_dir()
        doc = app.documents.add(
            adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        design.fusionUnitsManager.distanceDisplayUnits = \
            adsk.fusion.DistanceUnits.MillimeterDistanceUnits
        root = design.rootComponent
        imported = {}
        try:
            root.name = DESIGN_NAME
        except Exception:
            pass

        reference = new_child(root,
                              "Reference assembly - grounded, do not edit")
        for name, files in REFERENCE_GROUPS:
            import_group(app, reference, name, ref_dir, files, imported)

        cables = import_group(app, reference, CABLE_GROUP[0], ref_dir,
                              CABLE_GROUP[1], imported)
        try:
            cables.isLightBulbOn = False
        except Exception:
            pass

        adsk.doEvents()
        check_imports(imported)

        try:
            reference.isGroundToParent = True
        except Exception:
            try:
                reference.isGrounded = True
            except Exception:
                pass

        # Empty components to model the enclosure into, so the first save
        # already has somewhere for each part of the case to live.
        for name in CASE_COMPONENTS:
            new_child(root, name)

        app.activeViewport.fit()
        ui.messageBox(
            "Symm60HE reference assembly imported from:\n%s\n\n"
            "The reference is grounded. Model the case into the empty "
            "components beside it." % ref_dir)
    except Exception:
        if ui:
            ui.messageBox("Script failed:\n" + traceback.format_exc())
