"""Dimensioned Mill-Max 854/856 connector reference shapes for FreeCAD.

These are mechanical case-design models, not vendor-certified CAD. Dimensions
follow the selected 1 x 12, 1.27 mm-pitch parts and retain a separate maximum
spring-extension envelope so enclosure work cannot consume the contact stroke.
"""
import FreeCAD as App
import Part

CONTACTS = 12
PITCH = 1.27
BODY_LENGTH = 14.35
BODY_DEPTH = 1.90
SPRING_INITIAL_HEIGHT = 4.216
SPRING_STROKE = 1.016
TARGET_PROJECTION = 2.21
TARGET_TOTAL_HEIGHT = 2.46
BOARD_SPACING = 6.0
SPRING_WORKING_HEIGHT = BOARD_SPACING - TARGET_PROJECTION


def cbox(width, depth, height, z=0.0):
    return Part.makeBox(width, depth, height,
                        App.Vector(-width / 2, -depth / 2, z))


def contact_x_positions():
    return [(index - (CONTACTS - 1) / 2) * PITCH
            for index in range(CONTACTS)]


def spring_connector(z=0.0, height=SPRING_WORKING_HEIGHT):
    """854 working-position model, projecting upward from its PCB."""
    if not SPRING_INITIAL_HEIGHT - SPRING_STROKE <= height <= SPRING_INITIAL_HEIGHT:
        raise ValueError("spring height is outside the published stroke")
    housing_height = 1.10
    housing = cbox(BODY_LENGTH, BODY_DEPTH, housing_height, z)
    contacts = []
    for x in contact_x_positions():
        contacts.append(Part.makeCylinder(0.34, housing_height,
                                           App.Vector(x, 0, z)))
        contacts.append(Part.makeCylinder(
            0.24, height - 0.55, App.Vector(x, 0, z + 0.55)))
        # A short rounded cap makes the contact tip visible without extending
        # beyond the published working height used by the case keepout.
        contacts.append(Part.makeSphere(
            0.24, App.Vector(x, 0, z + height - 0.24),
            App.Vector(0, 0, 1), 0, 90, 360))
    return Part.makeCompound([housing] + contacts).removeSplitter()

def spring_motion_envelope(z=0.0):
    """Maximum 854 body/contact height reserved above the spring PCB."""
    return cbox(BODY_LENGTH, BODY_DEPTH, SPRING_INITIAL_HEIGHT, z)


def target_connector(z=0.0, height=TARGET_PROJECTION):
    """856 target model with its flat mating face at ``z``."""
    housing_height = 1.10
    housing = cbox(BODY_LENGTH, BODY_DEPTH, housing_height,
                   z + height - housing_height)
    contacts = []
    for x in contact_x_positions():
        contacts.append(Part.makeCylinder(0.535, 0.25,
                                           App.Vector(x, 0, z)))
        contacts.append(Part.makeCylinder(0.33, height,
                                           App.Vector(x, 0, z)))
    return Part.makeCompound([housing] + contacts).removeSplitter()
