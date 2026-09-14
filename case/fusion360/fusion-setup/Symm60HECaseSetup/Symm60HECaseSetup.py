"""Create a componentized Fusion case-design project for Symm60HE.

Every imported STEP is already in its checked global assembly position.  The
script groups the plate, switches and keycaps for each half, but keeps every
Hall PCB and daughterboard as a separate Fusion component.  Mounted connector
models follow their owning PCB; nonphysical travel/FPC volumes live in a
separate reference group.
"""
import json
import os
import traceback

import adsk.core
import adsk.fusion

REFERENCE_DIR = r"E:\Symm60HE-GitHub-Upload\Symm60HE\case\fusion360"
REFERENCE_FILE = "Symm60HE-case-reference-assembly.step"
COMPONENT_PLACEMENT_FILE = os.path.join(
    "generated", "component-placement.json")
DESIGN_NAME = "Symm60HE Case - Componentized v6 exact vendor pogo"
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


def import_part(app, parent, path, name, ground=False):
    target = parent.component if isinstance(parent, adsk.fusion.Occurrence) else parent
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
    for filename, part_name in files:
        path = os.path.join(ref_dir, filename)
        if not os.path.isfile(path):
            raise RuntimeError("Cannot find component STEP: " + path)
        occurrence = import_part(app, group, path, part_name)
        key = filename[len("Symm60HE-"):-len(".step")]
        registry[key] = occurrence
    return group


def validate_component_placements(registry, manifest_path, tolerance_mm=0.10):
    """Fail visibly if Fusion reinterprets a STEP component transform."""
    with open(manifest_path, "r", encoding="utf-8") as stream:
        expected = json.load(stream)
    problems = []
    for name, occurrence in registry.items():
        if name not in expected:
            problems.append(name + ": missing placement manifest entry")
            continue
        # preciseBoundingBox evaluates the imported B-rep rather than the
        # looser display/cache bounds. It is available in current Fusion; keep
        # the older property only as a compatibility fallback.
        try:
            box = occurrence.preciseBoundingBox
        except Exception:
            box = occurrence.boundingBox
        # Fusion API geometry uses centimetres; the generated manifest is mm.
        actual = [box.minPoint.x * 10.0, box.minPoint.y * 10.0,
                  box.minPoint.z * 10.0, box.maxPoint.x * 10.0,
                  box.maxPoint.y * 10.0, box.maxPoint.z * 10.0]
        error = max(abs(a - b) for a, b in zip(actual, expected[name]))
        if error > tolerance_mm:
            problems.append("%s: maximum bound error %.3f mm" % (name, error))
    if problems:
        raise RuntimeError(
            "Component placement verification failed:\n" + "\n".join(problems))


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
        imported = {}
        try:
            root.name = DESIGN_NAME
        except Exception:
            pass

        reference = new_child(root, "Reference assembly - grounded, do not edit")

        # One combined visual/mechanical datum per moving half.
        import_group(app, reference, "Left plate + switches + keycaps", ref_dir, (
            ("Symm60HE-LeftPlate.step", "Left plate"),
            ("Symm60HE-LeftSwitches.step", "Left switches"),
            ("Symm60HE-LeftKeycaps.step", "Left keycaps"),
        ), imported)
        import_group(app, reference, "Right plate + switches + keycaps", ref_dir, (
            ("Symm60HE-RightPlate.step", "Right plate"),
            ("Symm60HE-RightSwitches.step", "Right switches"),
            ("Symm60HE-RightKeycaps.step", "Right keycaps"),
        ), imported)

        # Each Hall PCB is independent; its directly mounted target connector
        # follows it into the same component.
        import_group(app, reference, "Left Hall-effect PCB", ref_dir, (
            ("Symm60HE-LeftPCB.step", "Left 1.2 mm Hall PCB"),
            ("Symm60HE-LeftPCBComponents.step", "Left fitted components"),
            ("Symm60HE-LeftTargetConnector.step", "Left pogo target"),
        ), imported)
        import_group(app, reference, "Right Hall-effect PCB", ref_dir, (
            ("Symm60HE-RightPCB.step", "Right 1.2 mm Hall PCB"),
            ("Symm60HE-RightPCBComponents.step", "Right fitted components"),
            ("Symm60HE-RightTargetConnector.step", "Right pogo target"),
        ), imported)

        # Floating pogo daughterboards stay independent so their capture and
        # permitted motion can be designed directly in the case.
        import_group(app, reference, "Left pogo daughterboard", ref_dir, (
            ("Symm60HE-LeftSpringPCB.step", "Left floating pogo PCB"),
            ("Symm60HE-LeftSpringConnector.step", "Left spring pogo block"),
            ("Symm60HE-LeftSpringFFCConnector.step", "Left FPC connector"),
        ), imported)
        import_group(app, reference, "Right pogo daughterboard", ref_dir, (
            ("Symm60HE-RightSpringPCB.step", "Right floating pogo PCB"),
            ("Symm60HE-RightSpringConnector.step", "Right spring pogo block"),
            ("Symm60HE-RightSpringFFCConnector.step", "Right FPC connector"),
        ), imported)

        # The flat controller is also independent.  The exact HRO receptacle's
        # checked world transform is baked into its standalone STEP so Fusion
        # never needs to reinterpret the vendor model's private origin.
        controller = import_group(
            app, reference, "Central controller daughterboard", ref_dir, (
                ("Symm60HE-DaughterboardPCB.step", "Controller PCB"),
                ("Symm60HE-DaughterboardComponents.step",
                 "Controller fitted components"),
                ("Symm60HE-LeftControllerFFC.step", "Left controller FPC"),
                ("Symm60HE-RightControllerFFC.step", "Right controller FPC"),
                ("Symm60HE-ControllerUSBConnector.step",
                 "Actual HRO TYPE-C-31-M-12 USB-C receptacle"),
            ), imported)

        # Keep nonphysical design volumes out of the board components so they
        # can be hidden together without hiding real hardware.
        keepouts = import_group(app, reference, "Cable and movement keepouts", ref_dir, (
            ("Symm60HE-ControllerUSBPlugEnvelope.step", "USB plug keepout"),
            ("Symm60HE-LeftPogoTravelEnvelope.step", "Left pogo travel"),
            ("Symm60HE-RightPogoTravelEnvelope.step", "Right pogo travel"),
            ("Symm60HE-LeftFFCEnvelope.step", "Left flexible FPC route"),
            ("Symm60HE-RightFFCEnvelope.step", "Right flexible FPC route"),
        ), imported)
        # These are nonphysical clearance volumes. Keep them in the project for
        # enclosure design, but do not let the USB plug box obscure the actual
        # receptacle when the project first opens.
        try:
            keepouts.isLightBulbOn = False
        except Exception:
            pass
        placement_manifest = os.path.join(ref_dir, COMPONENT_PLACEMENT_FILE)
        if not os.path.isfile(placement_manifest):
            raise RuntimeError("Cannot find component placement manifest: " +
                               placement_manifest)
        adsk.doEvents()
        validate_component_placements(imported, placement_manifest)

        try:
            reference.isGroundToParent = True
        except Exception:
            try:
                reference.isGrounded = True
            except Exception:
                pass

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
            "Symm60HE in-case reference imported as a grounded component tree.\n\n"
            "Included:\n"
            "- one plate/switch/keycap component per half\n"
            "- independent left/right Hall PCB components\n"
            "- independent controller and left/right pogo daughterboards\n"
            "- mirrored 3 degree tent and 7 degree typing angle\n"
            "- direct target connectors and mated floating pogo heads\n"
            "- flat left-to-right controller with rear-facing USB-C keepout\n"
            "- exact HRO TYPE-C-31-M-12 USB-C receptacle at J1\n"
            "- footprint-aligned FPC-compatible ZIF bodies and flexible route envelopes\n\n"
            "All imported component bounds passed the placement manifest.\n\n"
            "The compact 20 x 6 mm floating heads clear one another while "
            "their spring and target contacts remain mated.\n\n"
            "Create the enclosure only in 'Case - model here'.\n\nSaved as: "
            + saved_to,
            "Symm60HE setup")
    except Exception:
        if ui:
            ui.messageBox("Symm60HE setup failed:\n\n" + traceback.format_exc(),
                          "Symm60HE setup")
