"""Create a Fusion case-design project from the integrated Symm60HE stack.

The imported master STEP already contains the tented plates, aligned 1.2 mm
Hall PCBs, switches/keycaps, direct target connectors, floating spring-head
PCBs, mated pogo blocks, flexible-FFC envelopes and flat controller. This
script deliberately applies no additional transforms in Fusion.
"""
import os
import traceback

import adsk.core
import adsk.fusion

REFERENCE_DIR = r"E:\Symm60HE-GitHub-Upload\Symm60HE\case\fusion360"
REFERENCE_FILE = "Symm60HE-case-reference-assembly.step"
DESIGN_NAME = "Symm60HE Case"
SAVE_DESIGN = True
CASE_COMPONENTS = ["Left top", "Left bottom", "Right top", "Right bottom",
                   "Centre blocker and controller housing"]


def resolve_reference_dir():
    here = os.path.dirname(os.path.abspath(__file__))
    for path in (REFERENCE_DIR, os.path.abspath(os.path.join(here, "..", ".."))):
        if os.path.isfile(os.path.join(path, REFERENCE_FILE)):
            return path
    raise RuntimeError(
        "Cannot find %s. Set REFERENCE_DIR at the top of this script to the "
        "repository's case/fusion360 folder." % REFERENCE_FILE)


def new_child(parent, name):
    component = parent.component if isinstance(parent, adsk.fusion.Occurrence) else parent
    occurrence = component.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occurrence.component.name = name
    return occurrence


def import_master(app, parent, path):
    target = parent.component if isinstance(parent, adsk.fusion.Occurrence) else parent
    before = target.occurrences.count
    options = app.importManager.createSTEPImportOptions(path)
    options.isViewFit = False
    app.importManager.importToTarget(options, target)
    if target.occurrences.count <= before:
        raise RuntimeError("Fusion reported no imported occurrence for " + path)
    occurrence = target.occurrences.item(target.occurrences.count - 1)
    occurrence.component.name = "Complete in-case reference - do not edit"
    try:
        occurrence.isGroundToParent = True
    except Exception:
        try:
            occurrence.isGrounded = True
        except Exception:
            pass
    return occurrence


def run(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    try:
        ref_dir = resolve_reference_dir()
        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        design.fusionUnitsManager.distanceDisplayUnits = \
            adsk.fusion.DistanceUnits.MillimeterDistanceUnits
        root = design.rootComponent
        try:
            root.name = DESIGN_NAME
        except Exception:
            pass

        reference = new_child(root, "Reference - grounded, do not edit")
        import_master(app, reference, os.path.join(ref_dir, REFERENCE_FILE))
        adsk.doEvents()

        case = new_child(root, "Case - model here")
        for name in CASE_COMPONENTS:
            new_child(case, name)
        case.activate()
        app.activeViewport.fit()

        saved_to = "not saved automatically"
        if SAVE_DESIGN:
            try:
                project = app.data.activeProject
                folder = None
                for index in range(project.rootFolder.dataFolders.count):
                    candidate = project.rootFolder.dataFolders.item(index)
                    if candidate.name == DESIGN_NAME:
                        folder = candidate
                        break
                if folder is None:
                    folder = project.rootFolder.dataFolders.add(DESIGN_NAME)
                doc.saveAs(
                    DESIGN_NAME, folder,
                    "Integrated case reference: 3 degree mirrored tent, 7 "
                    "degree typing angle, 1.2 mm PCBs and mated pogo heads.", "")
                saved_to = project.name + " / " + DESIGN_NAME
            except Exception as exc:
                saved_to = "automatic save unavailable (%s); use File > Save" % exc

        ui.messageBox(
            "Symm60HE in-case reference imported as one grounded assembly.\n\n"
            "Included:\n"
            "- plates with aligned Hall PCBs, switches and keycaps\n"
            "- mirrored 3 degree tent and 7 degree typing angle\n"
            "- direct target connectors and mated floating pogo heads\n"
            "- flat left-to-right controller with rear-facing USB-C keepout\n"
            "- footprint-aligned FFC bodies and flexible route envelopes\n\n"
            "The compact 20 x 6 mm floating heads clear one another while "
            "their spring and target contacts remain mated.\n\n"
            "Create the enclosure only in 'Case - model here'.\n\nSaved as: "
            + saved_to,
            "Symm60HE setup")
    except Exception:
        if ui:
            ui.messageBox("Symm60HE setup failed:\n\n" + traceback.format_exc(),
                          "Symm60HE setup")
