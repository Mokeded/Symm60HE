"""Emit the three Symm60HE boards.

Everything sits on the front copper: the sensor at each key centre and its two
decoupling caps in the cell corners, clear of the 14 mm switch body.  That is a
deliberate departure from FN40HE, which mounts sensors on the back -- it keeps
the whole board free of mirrored geometry, which cannot be checked here.
"""
import os, math, uuid, csv, sys
sys.path.insert(0, ".")
from sexp import loads, dumps, find, first, Sym, set_uuids
from flip import flip as flip_fp, set_pad_angles
from geom import KEYS, U, AXIS
from outline import LEFT_PCB, RIGHT_PCB, DB, CASE_IN, axis_mm
from shapely.geometry import Polygon
from shapely.affinity import rotate as srot, translate as stran
from shapely.geometry import box as sbox, Point as spoint
from shapely.ops import unary_union

FPDIR = "../Symm60HE_Project.pretty"
HEADER = open("pcb_header.txt").read() if os.path.exists("pcb_header.txt") else None
LIB = "Symm60HE_Project"

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
    fp[1] = "%s:%s" % (LIB, name)
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
        cells.append(stran(srot(sbox(-w/2, -9.525, w/2, 9.525), -k["rot"], origin=(0, 0)),
                           k["cx"] * U, k["cy"] * U))
        if k["w"] >= 2.0:
            # Stabiliser holes reach past the cell: 11.9 mm out, and the lower
            # 3.988 mm hole bottoms out 10.25 mm down.  Union the holes in
            # directly with a 1.5 mm rim -- a box round them still gets clipped
            # by the hull's diagonal at the spacebar corner.
            for sx in (-STAB_X, STAB_X):
                for dy, dia in ((-6.985, 3.048), (8.255, 3.9878)):
                    cells.append(stran(srot(spoint(sx, dy).buffer(dia/2 + 1.5), -k["rot"],
                                            origin=(0, 0)), k["cx"] * U, k["cy"] * U))
    stabs = [c for c in cells if c.area < 80]          # the hole discs
    hull = unary_union(cells).convex_hull.buffer(RIM)
    hull = unary_union([hull] + [c.buffer(RIM) for c in stabs])
    lim = (sbox(-1e4, -1e4, axis_mm - MID_GAP/2, 1e4) if half == "L"
           else sbox(axis_mm + MID_GAP/2, -1e4, 1e4, 1e4))
    g = hull.intersection(CASE_IN.buffer(-0.8)).intersection(lim)
    return max(g.geoms, key=lambda p: p.area) if hasattr(g, "geoms") else g

for half, poly, fname in (("L", tight_pcb("L"), "Symm60HE-Left"), ("R", tight_pcb("R"), "Symm60HE-Right")):
    groups, ks = channels(half)
    fps, nsens, ncap, nstab = [], 0, 0, 0
    ks_sorted = sorted(ks, key=lambda k: (round(k["cy"], 2), k["cx"]))
    for i, k in enumerate(ks_sorted, 1):
        x, y, r = k["cx"] * U, k["cy"] * U, -k["rot"]
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
        a = -k["rot"]
        def local(dx, dy, w, h):
            return stran(srot(sbox(dx-w/2, dy-h/2, dx+w/2, dy+h/2), a, origin=(0, 0)),
                         k["cx"] * U, k["cy"] * U)
        busy.append(local(0, 0, 6.0, 5.0))              # MT9102ET + its pads
        busy.append(local(0, -5.08, 2.8, 2.8))          # MX leg holes
        busy.append(local(0,  5.08, 2.8, 2.8))
        for dx, dy in CAP_OFF:
            busy.append(local(dx, dy, 2.6, 2.2))        # decouplers
        if k["w"] >= 2.0:
            for sx in (-STAB_X, STAB_X):
                busy.append(local(sx, -6.985, 4.2, 4.2))
                busy.append(local(sx,  8.255, 5.2, 5.2))

    # four 8:1 muxes, now free to sit under the key field
    b = poly.bounds
    taken = []
    for m in range(4):
        want = b[0] + (b[2] - b[0]) * (0.20 + 0.20 * m)
        spot = find_spot(poly, want, b[1] + (b[3] - b[1]) * 0.62, 9.0, 7.4, busy=busy, step=0.5)
        mx, my = spot
        taken.append((mx, my))
        busy.append(sbox(mx-5.6, my-4.6, mx+5.6, my+4.6))
        nets = {"3": "ADC_%s%d" % (half, m + 1), "6": "GND", "7": "GND",
                "8": "GND", "9": "MUX_A2", "10": "MUX_A1", "11": "MUX_A0", "16": "+3V3A"}
        for ch in range(8):
            idx = m * 8 + ch
            pin = {0: "13", 1: "14", 2: "15", 3: "12", 4: "1", 5: "5", 6: "2", 7: "4"}[ch]
            nets[pin] = "HE_%s%02d" % (half, idx + 1) if idx < len(groups) else "GND"
        fps.append(place("AM1_TSSOP-16_4.4x5mm_P0.65mm", "AM%s%d" % (half, m + 1),
                         "SN74LV4051A", mx, my, 90, nets=nets, back=True))
        cspot = find_spot(poly, mx + 6.2, my, 2.6, 2.2, busy=busy)
        busy.append(sbox(cspot[0]-1.3, cspot[1]-1.1, cspot[0]+1.3, cspot[1]+1.1))
        fps.append(place("C1_C_0402_1005Metric", "CM%s%d" % (half, m + 1), "100n",
                         cspot[0], cspot[1], 0, nets={"1": "+3V3A", "2": "GND"}, back=True))
    # ribbon connector, inner edge near the top
    want_x = (b[2] - 14.0) if half == "L" else (b[0] + 14.0)
    jrot = 0
    spot = find_spot(poly, want_x, b[1] + 10.0, 21.0, 8.0, busy=busy, step=0.5)
    if spot is None:
        jrot = 90
        spot = find_spot(poly, want_x, b[1] + 10.0, 8.0, 21.0, busy=busy, step=0.5)
    jx, jy = spot
    busy.append(sbox(jx-10.5, jy-4.0, jx+10.5, jy+4.0) if jrot == 0
                else sbox(jx-4.0, jy-10.5, jx+4.0, jy+10.5))
    busy.append(sbox(jx-11.5, jy-5.0, jx+11.5, jy+5.0))
    RIB = ["+3V3A", "GND", "MUX_A0", "MUX_A1", "MUX_A2", "GND",
           "ADC_%s1" % half, "GND", "ADC_%s2" % half, "GND",
           "ADC_%s3" % half, "ADC_%s4" % half]
    fps.append(place("FFC_12P_1.00mm_TopContact", "J%s1" % half, "FFC_12P",
                     jx, jy, jrot, nets={str(i + 1): n for i, n in enumerate(RIB)}, back=True))
    mh = 0
    for wx, wy, ddx, ddy in [(b[0]+14, b[1]+12, 1, 1), (b[0]+14, b[3]-12, 1, -1),
                             (b[2]-14, b[1]+12, -1, 1), (b[2]-14, b[3]-12, -1, -1)]:
        spot = find_spot(poly, wx, wy, 7.0, 7.0, busy=busy, step=0.5)
        if spot is None: continue
        busy.append(sbox(spot[0]-4, spot[1]-4, spot[0]+4, spot[1]+4))
        mh += 1
        fps.append(place("MountingHole_2.2mm_M2_Pad", "MH%s%d" % (half, mh),
                         "M2", spot[0], spot[1], 0, nets={"1": "GND"}))
    print("   %s: muxes at %s | FFC at (%.1f, %.1f) rot %d | %d mounting holes"
          % (half, ", ".join("(%.0f,%.0f)" % t for t in taken), jx, jy, jrot, mh))
    n = board(poly, fps, "../pcb/%s.kicad_pcb" % fname, fname)
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
# The MCU pin assignment below is a PLACEHOLDER.  There is no schematic yet, so
# it has not been checked against the AT32F405 datasheet -- the ADC channels,
# the USB pair and the crystal pins are all fixed in silicon and will move once
# it has been.  What it does do is put each signal on the side of the package
# that faces the part it has to reach, which is what makes the board routable
# at all: an LQFP-64 on 0.5 mm pitch has no room to carry a net round a corner.
_p = []
fps = []
db = DB
cx, cy = db.centroid.x, db.centroid.y
def at(dx, dy): return cx + dx, cy + dy

# USB-C receptacle keep-out, top edge, centred.  It is not a footprint yet, so
# it goes on the board as a drawing that the router and the checks both honour;
# without it parts and copper wander in under the connector.
USB_KO = sbox(cx - 4.5, db.bounds[1] + 0.5, cx + 4.5, db.bounds[1] + 8.0)

_p = [
  # left edge (1-16) faces the crystal, reset and the analog LDO; bottom edge
  # (17-32) faces both ribbons, with each half's ADC group at its own end and
  # the three select lines in the middle so they can fan either way; top edge
  # (49-64) faces the USB-C and the boot switch; right edge (33-48) carries the
  # digital rail and a second tap of the analog one, for the right ribbon.
  ("U4_LQFP-64_10x10mm_P0.5mm", "U1", "AT32F405RCT7", (0, 3), 0,
     {"1": "+3V3D", "5": "XTAL_IN", "6": "XTAL_OUT", "7": "NRST",
      "12": "GND", "13": "+3V3A",
      "17": "ADC_L1", "18": "ADC_L2", "19": "ADC_L3", "20": "ADC_L4",
      "22": "GND",
      "24": "MUX_A0", "25": "MUX_A1", "26": "MUX_A2",
      "28": "GND",
      "29": "ADC_R1", "30": "ADC_R2", "31": "ADC_R3", "32": "ADC_R4",
      "36": "+3V3D", "40": "+3V3A", "44": "GND",
      "49": "SWCLK", "51": "SWDIO", "53": "SWO",
      "56": "USB_DM", "57": "USB_DP", "58": "USB_R", "60": "BOOT0",
      "63": "+3V3D"}),
  # USB side, up by the receptacle: ESD array first, then the CC/ID resistor
  ("U1_SOT-23-6", "U2", "USBLC6-2SC6", (-7.5, -8.5), 0,
     {"1": "USB_DP", "2": "GND", "3": "USB_DM", "4": "USB_DM", "5": "VBUS", "6": "USB_DP"}),
  ("R3_R_0402_1005Metric", "R1", "12k", (-8.0, -4.0), 0, {"1": "USB_R", "2": "GND"}),
  ("F1_Fuse_0805_2012Metric", "F1", "0.5A", (7.0, -8.5), 0, {"1": "VBUS_IN", "2": "VBUS"}),
  ("C148_C_0603_1608Metric", "C1", "10u", (12.0, -8.5), 0, {"1": "VBUS", "2": "GND"}),
  # right edge: the digital rail, kept up out of the bottom lane the ADC runs
  # need to reach the right ribbon
  ("U2_SOT-23-5", "U3", "TLV75733PDBV", (14.0, -2.0), 0, {"1": "VBUS", "2": "GND", "5": "+3V3D"}),
  ("C148_C_0603_1608Metric", "C2", "1u", (19.5, -2.0), 0, {"1": "+3V3D", "2": "GND"}),
  # left edge: crystal, analog rail, reset
  ("Y1_Crystal_SMD_3225-4Pin_3.2x2.5mm", "Y1", "12MHz", (-12.5, 4.5), 0,
     {"1": "XTAL_IN", "2": "GND", "3": "XTAL_OUT", "4": "GND"}),
  ("U3_SOT-23-3", "U4", "XC6206P332MR", (-17.5, 3.0), 0,
     {"1": "GND", "2": "+3V3A", "3": "+3V3D"}),
  ("SW1_SW_Push_1P1T_XKB_TS-1187A", "SW2", "TS-1187A", (-16.5, -3.0), 0, {"1": "NRST", "2": "GND"}),
  # top edge: boot
  ("SW1_SW_Push_1P1T_XKB_TS-1187A", "SW1", "TS-1187A", (-15.0, -10.0), 0, {"1": "BOOT0", "2": "GND"}),
]
for fpn, ref, val, (dx, dy), rot, nets in _p:
    x, y = at(dx, dy)
    fps.append(place(fpn, ref, val, x, y, rot, nets=nets))

for half, dx, rot in (("L", -24.5, 90), ("R", 24.5, 270)):
    RIB = ["+3V3A", "GND", "MUX_A0", "MUX_A1", "MUX_A2", "GND",
           "ADC_%s1" % half, "GND", "ADC_%s2" % half, "GND",
           "ADC_%s3" % half, "ADC_%s4" % half]
    x, y = at(dx, 2.0)
    fps.append(place("FFC_12P_1.00mm_TopContact", "J%s" % ("2" if half == "L" else "3"),
                     "FFC_12P", x, y, rot,
                     nets={str(i + 1): n for i, n in enumerate(RIB)}))
n = board(db, fps, "../pcb/Symm60HE-Daughterboard.kicad_pcb", "Symm60HE-Daughterboard",
          drawings=outline_on(USB_KO, "Dwgs.User"))
print("daughterboard: %.1f x %.1f mm | %d footprints (MCU, USB ESD, 2 LDOs, xtal, fuse, 2 tacts, 2 FFC)"
      % (db.bounds[2]-db.bounds[0], db.bounds[3]-db.bounds[1], n))
