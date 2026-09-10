"""Parametric DOE-angle case, emitted as self-contained OpenSCAD.

Matches the DOE's published spec: 11 deg typing angle, isolated top mount,
front height inside the stated 14.7-20.1 mm.  The bottom is flat and the top
face is inclined -- a wedge -- rather than the whole box being tipped, which
is what a tray case actually is.

The DOE quotes no lateral tent, so lateral_tent_deg defaults to 0; it is left
as a parameter because a tented build was asked for and the geometry supports
it.  Raising it lifts the outer edges and the case then needs feet on one side.
"""
import math
from outline import CASE_OUT, CASE_IN, DB, axis_mm, WALL

TYPING     = 11.0    # DOE spec
LATERAL    = 0.0     # DOE has none; raise for a laterally tented build
FRONT_H    = 18.0    # inside the DOE's 14.7-20.1 mm front height
FLOOR      = 3.0
LEDGE_H    = 9.5
LEDGE_W    = 3.0
PLATE_T    = 1.5
GASKET     = 1.5
PCB_STANDOFF = 4.0
USB_W, USB_H = 12.0, 7.0

def pts(poly):
    c = list(poly.exterior.coords)[:-1]
    return "[" + ",".join("[%.3f,%.3f]" % (x, -y) for x, y in c) + "]"

# OpenSCAD y = -KiCad y, so larger y is further back and must be taller.
b = CASE_OUT.bounds
y_front, y_back = -b[3], -b[1]
depth = y_back - y_front
back_h = FRONT_H + depth * math.tan(math.radians(TYPING))

scad = """// DOE60 case -- generated, parametric.  Units mm.
// Bottom flat on the desk; top face inclined at the DOE's typing angle.

typing_angle_deg  = %(TYPING)s;   // DOE spec: 11 deg
lateral_tent_deg  = %(LATERAL)s;    // DOE quotes none; raise for a tented build
front_h           = %(FRONT_H)s;   // DOE front height is 14.7-20.1 mm
back_h            = %(BACK_H).2f;

floor_t      = %(FLOOR)s;
ledge_w      = %(LEDGE_W)s;
plate_t      = %(PLATE_T)s;
gasket_t     = %(GASKET)s;
wall         = %(WALL)s;
pcb_standoff = %(PCB_STANDOFF)s;
plate_to_pcb = 5.0;   // MX plate-to-PCB
pcb_t        = 1.6;
usb_w        = %(USB_W)s;
db_w         = %(DBW).1f;
db_h         = %(DBH).1f;
usb_h        = %(USB_H)s;

y_front = %(YF).3f;
y_back  = %(YB).3f;
axis_x  = %(AXIS).3f;

outer = %(OUTER)s;
inner = %(INNER)s;

// Half-spaces parallel to the inclined top face, `drop` mm below it.
module above_plane(drop) {
    translate([0, y_front, front_h - drop])
        rotate([typing_angle_deg, 0, 0])
            translate([-2000, -50, 0]) cube([4000, 4000, 2000]);
}
module below_plane(drop) {
    translate([0, y_front, front_h - drop])
        rotate([typing_angle_deg, 0, 0])
            translate([-2000, -50, -2000]) cube([4000, 4000, 2000]);
}

module outer_wedge() {
    difference() {
        linear_extrude(back_h + 20) polygon(outer);
        above_plane(0);                       // cut the inclined top face
    }
}

// The pocket floor runs parallel to the plate, the way a wedge tray case is
// actually milled -- a flat pocket floor would leave the rear standoffs as
// 30 mm pillars.
pocket_drop = gasket_t + plate_t + plate_to_pcb + pcb_t + pcb_standoff;

module interior() {
    // main cavity: inner outline, pocket floor up to the plate underside
    intersection() {
        linear_extrude(back_h + 30) polygon(inner);
        below_plane(gasket_t + plate_t);
        above_plane(pocket_drop);
    }
    // gasket + plate rebate: wider, from the plate underside out through the top
    intersection() {
        linear_extrude(back_h + 30) offset(delta = ledge_w) polygon(inner);
        above_plane(gasket_t + plate_t);
    }
    db_pocket();
}

// The daughterboard lives in the solid under the raised back -- the only place
// in this layout with room for it, since the number rows reach too close to the
// centre for a coplanar board.  Its pocket opens upward into the main cavity so
// the two ribbons can route, and the USB cutout opens into it through the back
// wall.
db_floor = 5.0;
module db_pocket() {
    translate([axis_x - db_w/2 - 4, y_back - wall - db_h - 8, db_floor])
        cube([db_w + 8, db_h + 8, back_h]);
}

module usb_cutout() {
    translate([axis_x, y_back, floor_t + pcb_standoff])
        translate([-usb_w/2, -wall*3, 0]) cube([usb_w, wall*6, usb_h]);
}

// Standoffs rise from the flat floor and are cut off level with the PCB, which
// hangs plate_to_pcb below the plate and so shares the top face's angle.
module standoff(x, y) {
    intersection() {
        translate([x, -y, 0]) difference() {
            cylinder(h = back_h + 30, d = 6, $fn = 32);
            translate([0, 0, -0.1]) cylinder(h = back_h + 40, d = 2.0, $fn = 24);
        }
        above_plane(pocket_drop);
        below_plane(pocket_drop - pcb_standoff);
    }
}

module case_body() {
    difference() {
        outer_wedge();
        interior();
        usb_cutout();
    }
    %(STANDOFFS)s
}

module case() {
    // lateral tent, if you want it: pivot about the centre line
    rotate([0, lateral_tent_deg, 0]) case_body();
}

case();
""" % dict(TYPING=TYPING, LATERAL=LATERAL, FRONT_H=FRONT_H, BACK_H=back_h,
           FLOOR=FLOOR, LEDGE_H=LEDGE_H, LEDGE_W=LEDGE_W, PLATE_T=PLATE_T,
           GASKET=GASKET, WALL=WALL, PCB_STANDOFF=PCB_STANDOFF,
           USB_W=USB_W, USB_H=USB_H,
           DBW=DB.bounds[2]-DB.bounds[0], DBH=DB.bounds[3]-DB.bounds[1], YF=y_front, YB=y_back, AXIS=axis_mm,
           OUTER=pts(CASE_OUT), INNER=pts(CASE_IN),
           STANDOFFS="\n    ".join(
               "standoff(%.2f, %.2f);" % (x, y) for x, y in [
                   (30, 8), (30, 95), (axis_mm-40, 8), (axis_mm-40, 100),
                   (axis_mm+40, 8), (axis_mm+40, 100),
                   (CASE_IN.bounds[2]-30, 8), (CASE_IN.bounds[2]-30, 95)]))

open("../case/DOE60-case.scad", "w").write(scad)
print("typing angle   %.1f deg (DOE spec)" % TYPING)
print("lateral tent   %.1f deg (DOE quotes none; parameter left in)" % LATERAL)
print("front height   %.1f mm  -> DOE spec is 14.7-20.1 mm: %s"
      % (FRONT_H, "inside" if 14.7 <= FRONT_H <= 20.1 else "OUTSIDE"))
print("back height    %.1f mm over %.1f mm of depth" % (back_h, depth))
pocket = GASKET + PLATE_T + 5.0 + 1.6 + PCB_STANDOFF
print("pocket floor   %.1f mm below the top face -> %.1f mm of material under it at the front"
      % (pocket, FRONT_H - pocket))
print("standoffs      %d x M2, %.1f mm, on a pocket floor parallel to the plate"
      % (8, PCB_STANDOFF))
print("daughterboard  pocket %.0f x %.0f mm in the back solid, floor at 5.0 mm"
      % (DB.bounds[2]-DB.bounds[0]+8, DB.bounds[3]-DB.bounds[1]+8))
print("wrote case/DOE60-case.scad")
