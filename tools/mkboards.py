"""Emit the three Symm60HE boards.

Both keyboard halves use B.Cu-only SMT assembly.  The compact controller keeps
its proven mixed-side placement and is ordered separately from the half-panel.
"""
import os, math, uuid, csv, sys
sys.path.insert(0, ".")
from sexp import loads, dumps, find, first, Sym, set_uuids
from flip import flip as flip_fp, set_pad_angles
from geom import KEYS, U, AXIS
from outline import LEFT_PCB, RIGHT_PCB, DB, CASE_IN, axis_mm, USB_X_OFF
from pcb.relocate_half_mounts import MOUNTS
from shapely.geometry import Polygon
from shapely.affinity import rotate as srot, translate as stran
from shapely.geometry import box as sbox, Point as spoint
from shapely.ops import unary_union

FPDIR = "../Symm60HE_Project.pretty"
HEADER = open("pcb_header.txt").read() if os.path.exists("pcb_header.txt") else None
LIB = "Symm60HE_Project"
PCB_OUT = os.environ.get("SYMM60HE_PCB_OUT", "../pcb")
os.makedirs(PCB_OUT, exist_ok=True)

# ---------------------------------------------------------------- channels ---
def channels(half):
    ks = [k for k in KEYS if k["half"] == half]
    for k in ks:
        a = math.radians(k["rot"]); c, s = math.cos(a), math.sin(a)
        hw, hh = k["w"]/2, 0.5
        k["poly"] = Polygon([(k["cx"]+dx*c-dy*s, k["cy"]+dx*s+dy*c)
                             for dx, dy in ((-hw,-hh),(hw,-hh),(hw,hh),(-hw,hh))]).buffer(-0.02)
    groups = []
    for k in sorted(ks, key=lambda k: -k["w"]):
        for g in groups:
            if all(k["poly"].intersection(o["poly"]).area > 0.05 for o in g):
                g.append(k); break
        else:
            groups.append([k])
    groups.sort(key=lambda g: (round(g[0]["cy"], 1), g[0]["cx"]))
    for i, g in enumerate(groups):
        for k in g:
            k["chan"] = i
            k["net"] = "HE_%s%02d" % (half, i + 1)
    return groups, ks

# ------------------------------------------------------------------ loader ---
_cache = {}
def load_fp(name):
    if name not in _cache:
        _cache[name] = open(os.path.join(FPDIR, name + ".kicad_mod")).read()
    return loads(_cache[name])

def place(name, ref, value, x, y, rot=0.0, nets=None, back=False):
    fp = load_fp(name)
    # Rotated Alice keys are emitted with placement-specific, rounded geometry
    # after the back-side mirror.  Keep those footprints board-local so KiCad
    # does not incorrectly compare them with the unplaced library template.
    # Ordinary components retain their library links and remain updateable.
    fp[1] = name if name.startswith("HE_KEY_") else "%s:%s" % (LIB, name)
    body = [c for c in fp[2:] if not (isinstance(c, list) and c[0] in ("version", "generator", "generator_version"))]
    out = [Sym("footprint"), fp[1], [Sym("layer"), "B.Cu" if back else "F.Cu"],
           [Sym("uuid"), str(uuid.uuid4())],
           [Sym("at"), round(x, 4), round(y, 4)] + ([round(rot, 3)] if rot else [])]
    for c in body:
        if not isinstance(c, list): continue
        if c[0] == "layer": continue
        if c[0] == "property" and c[1] == "Reference": c[2] = ref
        if c[0] == "property" and c[1] == "Value":     c[2] = value
        if c[0] == "pad" and nets:
            num = c[1]
            if num in nets:
                c.append([Sym("net"), nets[num]])
        out.append(c)
    if back:
        for c in out[5:]: flip_fp(c)
    set_pad_angles(out, rot)
    set_uuids(out)
    out[3] = [Sym("uuid"), str(uuid.uuid4())]
    return out

def edge(poly):
    pts = list(poly.exterior.coords)
    return [[Sym("gr_line"), [Sym("start"), round(a[0],4), round(a[1],4)],
             [Sym("end"), round(b[0],4), round(b[1],4)],
             [Sym("stroke"), [Sym("width"), 0.1], [Sym("type"), Sym("solid")]],
             [Sym("layer"), "Edge.Cuts"], [Sym("uuid"), str(uuid.uuid4())]]
            for a, b in zip(pts, pts[1:])]

def outline_on(poly, layer, width=0.15):
    pts = list(poly.exterior.coords)
    return [[Sym("gr_line"), [Sym("start"), round(a[0],4), round(a[1],4)],
             [Sym("end"), round(b[0],4), round(b[1],4)],
             [Sym("stroke"), [Sym("width"), width], [Sym("type"), Sym("solid")]],
             [Sym("layer"), layer], [Sym("uuid"), str(uuid.uuid4())]]
            for a, b in zip(pts, pts[1:])]

def board(polygon, footprints, path, title, drawings=()):
    hdr = loads(HEADER + ")")
    body = [c for c in hdr[1:]]
    body += edge(polygon)
    body += list(drawings)
    body += footprints
    doc = [Sym("kicad_pcb")] + body + [[Sym("embedded_fonts"), Sym("no")]]
    open(path, "w").write(dumps(doc) + "\n")
    return len(footprints)

def fits(poly, x, y, w, h, margin=1.0, busy=None):
    b = sbox(x-w/2, y-h/2, x+w/2, y+h/2)
    if not poly.buffer(-margin).contains(b): return False
    if busy is not None and any(b.intersects(o) for o in busy): return False
    return True

def find_spot(poly, x, y, w, h, dx=0.0, dy=0.0, margin=1.0, busy=None, step=1.0):
    """Nearest point to (x, y) where the part sits inside the board and clear of
    everything already placed.  Grid search -- a directional walk gets trapped."""
    if fits(poly, x, y, w, h, margin, busy): return x, y
    b = poly.bounds
    best, bd = None, 1e18
    ny = b[1] + margin
    while ny <= b[3] - margin:
        nx = b[0] + margin
        while nx <= b[2] - margin:
            d = (nx - x) ** 2 + (ny - y) ** 2
            if d < bd and fits(poly, nx, ny, w, h, margin, busy):
                best, bd = (nx, ny), d
            nx += step
        ny += step
    return best

# -------------------------------------------------------------------- halves --
CAP_OFF = [(-6.6, -6.9), (6.6, 6.9)]        # opposite cell corners, clear of the 14 mm body
STAB_X = 11.90625
report = {}

RIM, MID_GAP = 2.0, 2.0
def tight_pcb(half):
    cells = []
    for k in KEYS:
        if k["half"] != half: continue
        w = max(k["w"] * U, 19.05)
        # A stabilizer's lower 3.99 mm drill reaches 10.25 mm from key centre.
        # Extend the entire wide-key cell as a straight, key-aligned edge; this
        # preserves clearance without reintroducing circular outline lobes.
        lower = 12.5 if k["w"] >= 2.0 else 9.525
        cells.append(stran(srot(sbox(-w/2, -9.525, w/2, lower), k["rot"], origin=(0, 0)),
                           k["cx"] * U, k["cy"] * U))
        # The 2u/2.25u key cell plus the common 2 mm rim already contains the
        # full stabilizer drill envelope.  Adding circular drill buffers to the
        # outline created unrelated scallops at the board edge.
    # Follow the actual keymap instead of wrapping it in a convex hull.  The
    # square/mitred join preserves the stepped row silhouette; the two cleanup
    # buffers remove microscopic self-intersections without rounding it away.
    hull = unary_union(cells).buffer(RIM, join_style=2)
    hull = hull.buffer(0.05, join_style=2).buffer(-0.05, join_style=2)
    # Each half needs one narrow inner-edge tongue for its 12-pin FFC.  This is
    # the only deliberate departure from the keymap silhouette and is kept to
    # the connector courtyard rather than restoring a large central wedge.
    tab_x = axis_mm - 7.0 if half == "L" else axis_mm + 7.0
    connector_tab = (sbox(tab_x - 6.0, 43.5, axis_mm, 68.5)
                     if half == "L"
                     else sbox(tab_x - 6.0, 43.5, tab_x + 6.0, 68.5))
    hull = unary_union([hull, connector_tab])
    lim = (sbox(-1e4, -1e4, axis_mm - MID_GAP/2, 1e4) if half == "L"
           else sbox(axis_mm + MID_GAP/2, -1e4, 1e4, 1e4))
    g = hull.intersection(CASE_IN.buffer(-0.8)).intersection(lim)
    return max(g.geoms, key=lambda p: p.area) if hasattr(g, "geoms") else g

# Use the shared mirrored envelopes from outline.py.  They contain the union of
# both halves' universal-layout requirements and are the authoritative PCB
# mechanics for regeneration.
for half, poly, fname in (("L", LEFT_PCB, "Symm60HE-Left"),
                          ("R", RIGHT_PCB, "Symm60HE-Right")):
    groups, ks = channels(half)
    fps, nsens, ncap, nstab = [], 0, 0, 0
    ks_sorted = sorted(ks, key=lambda k: (round(k["cy"], 2), k["cx"]))
    for i, k in enumerate(ks_sorted, 1):
        x, y, r = k["cx"] * U, k["cy"] * U, k["rot"]
        ref = "HE%s%d" % (half, i)
        fps.append(place("HE_KEY_%.2fu" % k["w"], ref, "MT9102ET", x, y, r,
                         nets={"1": "+3V3A", "2": "GND", "3": k["net"]}, back=True))
        nsens += 1
        a = math.radians(k["rot"])
        for j, (dx, dy) in enumerate(CAP_OFF):
            cx = x + dx*math.cos(a) - dy*math.sin(a)
            cy = y + dx*math.sin(a) + dy*math.cos(a)
            val, nm = ("100n", "C%s%dA") if j == 0 else ("4.7n", "C%s%dB")
            fps.append(place("C1_C_0402_1005Metric", nm % (half, i), val, cx, cy, r,
                             nets={"1": "+3V3A" if j == 0 else k["net"], "2": "GND"}, back=True))
            ncap += 1
        if k["w"] >= 2.0:
            nstab += 1
            fps.append(place("STABILIZER_MX_2U", "S%s%d" % (half, nstab),
                             "STAB_MX", x, y, r))
    # Occupancy on the back copper.  Only real obstructions block a part here:
    # the sensor body, the two MX leg holes, the stabiliser holes and the
    # decouplers already placed.  The rest of each cell's underside is free,
    # which is what lets the muxes hide under the key field.
    busy = []
    for k in ks_sorted:
        a = k["rot"]
        def local(dx, dy, w, h):
            return stran(srot(sbox(dx-w/2, dy-h/2, dx+w/2, dy+h/2), a, origin=(0, 0)),
                         k["cx"] * U, k["cy"] * U)
        busy.append(local(0, 0, 6.0, 5.0))              # MT9102ET + its pads
        busy.append(local(0, -5.08, 2.8, 2.8))          # MX leg holes
        busy.append(local(0,  5.08, 2.8, 2.8))
        for dx, dy in CAP_OFF:
            busy.append(local(dx, dy, 2.6, 2.2))        # decouplers
        if k["w"] >= 2.0:
            # not just the two hole pairs: the stabiliser's wire runs between
            # them, so the whole envelope is off limits to anything with a body
            busy.append(local(0, 0.635, 2*STAB_X + 5.2, 20.4))

    # Four 8:1 muxes, free to sit under the key field.  SOIC-16 laid on its
    # side is 10.8 x 7.4 mm of courtyard, so the placement search and the
    # occupancy box below both have to be told the bigger number -- with the
    # TSSOP figures still in they overlap the sensor and decoupler pads.
    b = poly.bounds
    taken = []
    for m in range(4):
        want = b[0] + (b[2] - b[0]) * (0.20 + 0.20 * m)
        spot = find_spot(poly, want, b[1] + (b[3] - b[1]) * 0.62,
                         11.6, 8.2, busy=busy, step=0.5)
        if spot is None:
            raise RuntimeError("no legal placement for AM%s%d" % (half, m + 1))
        mx, my = spot
        taken.append((mx, my))
        busy.append(sbox(mx-5.9, my-4.2, mx+5.9, my+4.2))
        nets = {"3": "ADC_%s%d" % (half, m + 1), "6": "GND", "7": "GND",
                "8": "GND", "9": "MUX_A2", "10": "MUX_A1", "11": "MUX_A0", "16": "+3V3A"}
        for ch in range(8):
            idx = m * 8 + ch
            pin = {0: "13", 1: "14", 2: "15", 3: "12", 4: "1", 5: "5", 6: "2", 7: "4"}[ch]
            nets[pin] = "HE_%s%02d" % (half, idx + 1) if idx < len(groups) else "GND"
        fps.append(place("AM1_SOIC-16_3.9x9.9mm_P1.27mm", "AM%s%d" % (half, m + 1),
                         "SN74LV4051A", mx, my, 90, nets=nets, back=True))
        cspot = find_spot(poly, mx + 7.2, my, 2.6, 2.2, busy=busy)
        busy.append(sbox(cspot[0]-1.3, cspot[1]-1.1, cspot[0]+1.3, cspot[1]+1.1))
        fps.append(place("C1_C_0402_1005Metric", "CM%s%d" % (half, m + 1), "100n",
                         cspot[0], cspot[1], 0, nets={"1": "+3V3A", "2": "GND"}, back=True))
    # Ribbon connectors occupy their dedicated inner tongues. JL1 is rotated
    # opposite JR1 so the two flex entries are mechanically mirrored rather
    # than forcing the left cable to fold back over its connector.
    want_x = axis_mm - 3.0 if half == "L" else axis_mm + 3.0
    jrot = 270 if half == "L" else 90
    # JL1 deliberately overhangs the connector tongue slightly so the flex can
    # enter from the centre seam; its copper remains inside Edge.Cuts and was
    # independently checked by KiCad DRC. The generic body-inside-board search
    # would reject that intentional mechanical overhang.
    spot = ((want_x, 56.0) if half == "L" else
            find_spot(poly, want_x, 56.0, 8.0, 21.0,
                      busy=busy, step=0.5))
    if spot is None:
        raise RuntimeError("no legal inner-tongue placement for J%s1" % half)
    jx, jy = spot
    busy.append(sbox(jx-10.5, jy-4.0, jx+10.5, jy+4.0) if jrot == 0
                else sbox(jx-4.0, jy-10.5, jx+4.0, jy+10.5))
    busy.append(sbox(jx-11.5, jy-5.0, jx+11.5, jy+5.0))
    RIB = ["+3V3A", "GND", "MUX_A0", "MUX_A1", "MUX_A2", "GND",
           "ADC_%s1" % half, "GND", "ADC_%s2" % half, "GND",
           "ADC_%s3" % half, "ADC_%s4" % half]
    pin_order = list(reversed(RIB)) if half == "L" else RIB
    fps.append(place("FFC_12P_1.00mm_TopContact", "J%s1" % half, "FFC_12P",
                     jx, jy, jrot,
                     nets={str(i + 1): n for i, n in enumerate(pin_order)}, back=True))
    mount_side = "Left" if half == "L" else "Right"
    for ref, spot in MOUNTS[mount_side].items():
        busy.append(sbox(spot[0]-2, spot[1]-2, spot[0]+2, spot[1]+2))
        fps.append(place("MountingHole_2.2mm_M2_NPTH", ref,
                         "M2_NPTH", spot[0], spot[1], 0))
    mh = len(MOUNTS[mount_side])
    print("   %s: muxes at %s | FFC at (%.1f, %.1f) rot %d | %d mounting holes"
          % (half, ", ".join("(%.0f,%.0f)" % t for t in taken), jx, jy, jrot, mh))
    n = board(poly, fps, os.path.join(PCB_OUT, "%s.kicad_pcb" % fname), fname)
    report[half] = dict(pos=len(ks), chan=len(groups), sens=nsens, caps=ncap,
                        stabs=nstab, fps=n, size=(poly.bounds[2]-poly.bounds[0],
                                                  poly.bounds[3]-poly.bounds[1]))

for h in ("L", "R"):
    r = report[h]
    print("%s half: %.1f x %.1f mm | %d switch positions -> %d channels | %d sensors, %d caps, %d stabs | %d footprints"
          % (h, r["size"][0], r["size"][1], r["pos"], r["chan"], r["sens"], r["caps"], r["stabs"], r["fps"]))

# --------------------------------------------------------------- daughterboard --
# Laid out on an explicit grid, relative to the board centre, so nothing has to
# be guessed: USB-C on the top edge, MCU centred, the two ribbon links end-on so
# the cables run straight out to each half.
#
# The MCU pin assignment and its support circuit follow the proven FN40HE
# reference design.  Core circuitry and support passives use opposite sides to
# preserve the compact daughterboard outline (57 x 28 mm after allowing the
# full C20111 hold-down lands at both outward-facing cable mouths).
_p = []
fps = []
db = DB
cx, cy = db.centroid.x, db.centroid.y
def at(dx, dy): return cx + dx, cy + dy

_p = [
  # The pin assignment is FN40HE's, read off its board rather than invented:
  # crystal on 5/6, reset on 7, the three mux selects on 9/10/11, the analog
  # rail on 13, the eight multiplexed analog inputs on 17 and 20-26, the USB
  # pair and its reference resistor on 33/34/35, and SWD on 46/49/55.  The
  # parts are then placed to suit it -- crystal, reset and the analog LDO off
  # the left edge, both ribbons below the bottom edge where the eight analog
  # inputs come out, USB and the digital rail off the right, boot above.
  ("U4_LQFP-64_10x10mm_P0.5mm", "U1", "AT32F405RCT7", (-1.5, 2), 0,
     {"1": "+3V3D", "5": "XTAL_IN", "6": "XTAL_OUT", "7": "NRST",
      "9": "MUX_A0", "10": "MUX_A1", "11": "MUX_A2",
      "12": "GND", "13": "+3V3A",
      "17": "ADC_L1", "20": "ADC_L2", "21": "ADC_L3", "22": "ADC_L4",
      "23": "ADC_R1", "24": "ADC_R2", "25": "ADC_R3", "26": "ADC_R4",
      "31": "GND", "33": "USB_R", "34": "USB_DM", "35": "USB_DP", "36": "+3V3D",
      "46": "SWDIO", "49": "SWCLK", "55": "SWO", "60": "BOOT0",
      "63": "GND", "64": "+3V3D"}),
  # USB side, all of it on the right: receptacle, ESD array and the reference
  # resistor sit beside the MCU pins that use them, which leaves the whole
  # bottom of the board as one clear lane for the eight analog inputs to reach
  # the two ribbons
  ("U1_SOT-23-6", "U2", "USBLC6-2SC6", (9.5, -3.5), 0,
     {"1": "USB_DP", "2": "GND", "3": "USB_DM", "4": "USB_DM", "5": "VBUS", "6": "USB_DP"}),
  ("R3_R_0402_1005Metric", "R1", "12k", (8.0, 0.0), 0, {"1": "USB_R", "2": "GND"}),
  ("F1_Fuse_0805_2012Metric", "F1", "0.5A", (17.0, -10.0), 0, {"1": "VBUS_IN", "2": "VBUS"}),
  ("C148_C_0603_1608Metric", "C1", "10u", (19.0, -6.5), 0, {"1": "VBUS", "2": "GND"}),
  # right edge: the digital rail, off pin 36
  ("U2_SOT-23-5", "U3", "TLV75733PDBV", (15.5, -3.5), 0, {"1": "VBUS", "2": "GND", "5": "+3V3D"}),
  ("C148_C_0603_1608Metric", "C2", "1u", (18.0, 6.0), 0, {"1": "+3V3D", "2": "GND"}),
  # USB-C receptacle, rotated so its mating face is on the top board edge.
  # A USB device must present Rd on both CC pins; omitting these two 5.1k
  # resistors prevents a compliant Type-C host from enabling VBUS.
  ("USB_C_Receptacle_HRO_TYPE-C-31-M-12", "J1", "TYPE-C-31-M-12",
     (USB_X_OFF, db.bounds[1] - cy + 3.65), 180,
     {"A1": "GND", "A4": "VBUS_IN", "A5": "CC1", "A6": "USB_DP", "A7": "USB_DM",
      "A9": "VBUS_IN", "A12": "GND", "B1": "GND", "B4": "VBUS_IN",
      "B5": "CC2", "B6": "USB_DP", "B7": "USB_DM", "B9": "VBUS_IN",
      "B12": "GND", "SH": "GND"}),
  ("R3_R_0402_1005Metric", "R2", "5.1k", (4.0, -4.0), 0, {"1": "CC1", "2": "GND"}),
  ("R3_R_0402_1005Metric", "R3", "5.1k", (11.0, 8.0), 0, {"1": "CC2", "2": "GND"}),
  # left edge: crystal on 5/6, analog rail on 13, reset on 7
  ("Y1_Crystal_SMD_3225-4Pin_3.2x2.5mm", "Y1", "12MHz", (-12.5, 1.0), 0,
     {"1": "XTAL_IN", "2": "GND", "3": "XTAL_OUT", "4": "GND"}),
  ("U3_SOT-23-3", "U4", "XC6206P332MR", (-12.5, 6.0), 0,
     {"1": "GND", "2": "+3V3A", "3": "+3V3D"}),
  ("SW1_SW_Push_1P1T_XKB_TS-1187A", "SW2", "TS-1187A", (-16.5, -4.0), 0, {"1": "NRST", "2": "GND"}),
  # top edge: boot, off pin 60, clear of the receptacle
  ("SW1_SW_Push_1P1T_XKB_TS-1187A", "SW1", "TS-1187A", (-12.5, -10.0), 0, {"1": "BOOT0", "2": "GND"}),
]
for fpn, ref, val, (dx, dy), rot, nets in _p:
    x, y = at(dx, dy)
    fps.append(place(fpn, ref, val, x, y, rot, nets=nets))

# Required MCU, oscillator and regulator support parts.  These were absent in
# the first placement-only draft; without them BOOT0 floats, the crystal has no
# specified load, and the supply rails are inadequately bypassed.  Values and
# connectivity match FN40HE.  B.Cu placement keeps them close to the relevant
# pins without enlarging the daughterboard.
_support = [
  ("R3_R_0402_1005Metric", "R4",  "12k",  (-6.4, -6.0), 90, {"1": "BOOT0",   "2": "GND"}),
  ("C1_C_0402_1005Metric", "C3",  "30p",  (-3.2, 11.8),  0, {"1": "XTAL_IN", "2": "GND"}),
  ("C1_C_0402_1005Metric", "C4",  "30p",  (-1.2, 11.8),  0, {"1": "XTAL_OUT","2": "GND"}),
  ("C1_C_0402_1005Metric", "C5",  "100n", (-6.2, -2.6),  0, {"1": "+3V3D",   "2": "GND"}),
  ("C1_C_0402_1005Metric", "C6",  "100n", ( 5.6,  4.3),  0, {"1": "+3V3D",   "2": "GND"}),
  ("C1_C_0402_1005Metric", "C7",  "100n", (-6.4, -4.6),  0, {"1": "+3V3D",   "2": "GND"}),
  ("C148_C_0603_1608Metric", "C8", "10u",  ( 6.3,  1.8),  0, {"1": "+3V3D",   "2": "GND"}),
  ("C1_C_0402_1005Metric", "C9",  "100n", ( 2.8, 11.8),  0, {"1": "+3V3A",   "2": "GND"}),
  ("C148_C_0603_1608Metric", "C10", "1u", ( 5.3, 11.8),  0, {"1": "+3V3A",   "2": "GND"}),
  ("C1_C_0402_1005Metric", "C11", "100n", ( 0.8, 11.8),  0, {"1": "NRST",     "2": "GND"}),
  ("C148_C_0603_1608Metric", "C12", "2.2u", (19.8, -4.2), 0, {"1": "VBUS",    "2": "GND"}),
  ("C148_C_0603_1608Metric", "C13", "2.2u", (18.0, -6.5), 0, {"1": "+3V3D",   "2": "GND"}),
  ("C148_C_0603_1608Metric", "C14", "2.2u", (-9.2, 10.8), 0, {"1": "+3V3D",   "2": "GND"}),
  ("C148_C_0603_1608Metric", "C15", "2.2u", (10.8, 11.8), 0, {"1": "+3V3A",   "2": "GND"}),
]
for fpn, ref, val, (dx, dy), rot, nets in _support:
    x, y = at(dx, dy)
    fps.append(place(fpn, ref, val, x, y, rot, nets=nets, back=True))

for half, dx, rot in (("L", -23.5, 90), ("R", 23.5, 270)):
    RIB = ["+3V3A", "GND", "MUX_A0", "MUX_A1", "MUX_A2", "GND",
           "ADC_%s1" % half, "GND", "ADC_%s2" % half, "GND",
           "ADC_%s3" % half, "ADC_%s4" % half]
    x, y = at(dx, 2.0)
    fps.append(place("FFC_12P_1.00mm_TopContact", "J%s" % ("2" if half == "L" else "3"),
                     "FFC_12P", x, y, rot,
                     nets={str(i + 1): n for i, n in enumerate(RIB)}))
# Two isolated M2 holes follow the compact Unified Daughterboard S-series
# retention idea: two points are sufficient for a small rigid PCB, and unlike
# four corner holes they do not force this board back to its original size.
# Mounting it wholly to one half avoids a rigid bridge across the tent hinge.
for i, (dx, dy) in enumerate(((-24.0, -11.0), (24.0, -11.0)), 1):
    x, y = at(dx, dy)
    fps.append(place("MountingHole_2.2mm_M2_NPTH", "MHD%d" % i, "M2_NPTH", x, y))
n = board(db, fps, os.path.join(PCB_OUT, "Symm60HE-Daughterboard.kicad_pcb"), "Symm60HE-Daughterboard")
print("daughterboard: %.1f x %.1f mm | %d footprints (MCU, USB-C/ESD/CC, 2 LDOs, xtal, complete support passives, fuse, 2 tacts, 2 FFC, 2 M2 NPTH)"
      % (db.bounds[2]-db.bounds[0], db.bounds[3]-db.bounds[1], n))
