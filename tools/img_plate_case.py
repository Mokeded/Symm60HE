import sys, math; sys.path.insert(0, ".")
from img import *
from geom import BUILDS
from shapely.geometry import box as sbox
from shapely.ops import unary_union
from shapely.affinity import rotate as srot2, translate as stran2

PLATE = CASE_IN.buffer(-0.5)
STAB_X, STAB = 11.90625, (7.0, 15.6, 0.635)
def plate_cuts(keys):
    cuts, stabs = [], []
    for k in keys:
        cuts.append(stran2(srot2(sbox(-7,-7,7,7), k["rot"], origin=(0,0)), k["cx"]*U, k["cy"]*U))
        if k["w"] >= 2.0:
            w,h,dy = STAB
            for sx in (-STAB_X, STAB_X):
                stabs.append(stran2(srot2(sbox(sx-w/2, dy-h/2, sx+w/2, dy+h/2), k["rot"], origin=(0,0)),
                                    k["cx"]*U, k["cy"]*U))
    return cuts, stabs

# ------------------------------------------------------------------ 5. plate
ks = [k for k in KEYS if "doe-wkl" in k["builds"]]
cuts, stabs = plate_cuts(ks)
c = Canvas(PLATE.bounds, 1900, foot=48)
c.poly(PLATE, fill=(120,130,140), outline=(231,236,239), w=1.0)
for x in cuts:  c.poly(x, fill=(18,22,26))
for x in stabs: c.poly(x, fill=(18,22,26))
fy = c.im.height/SS - 32
c.raw_text((16, fy), "DOE60 plate — filled WKL, 1.5u backspace   328.0 x 117.2 mm   60 switch cutouts at 14.0 mm", INK, 11)
c.raw_text((16, fy+15), "4.90 mm minimum bridge between openings   |   10.79 mm from plate edge to nearest cutout   |   one DXF per layout in plate/", DIM, 9.5)
print("plate", c.save("05-plate.png"))

# --------------------------------------------------------- 6. case section
TYPING, FRONT_H = 11.0, 18.0
GASKET, PLATE_T, P2P, PCB_T, STAND = 1.5, 1.5, 5.0, 1.6, 4.0
POCKET = GASKET+PLATE_T+P2P+PCB_T+STAND
WALL = 3.0
b = CASE_OUT.bounds; depth = b[3]-b[1]; t = math.tan(math.radians(TYPING))
def top(u): return FRONT_H + (depth-u)*t
def zz(u,d): return top(u)-d
c = Canvas((0, -46, depth, 4), 1700, pad=30, foot=52)
def P(u, z): return (u, -z)
def quad(pts, **kw): c.poly(Polygon([P(*p) for p in pts]), **kw)
quad([(0,0),(depth,0),(depth,top(depth)),(0,top(0))], fill=(42,50,58), outline=(92,180,222), w=1.0)
quad([(WALL,zz(WALL,POCKET)),(depth-WALL,zz(depth-WALL,POCKET)),
      (depth-WALL,zz(depth-WALL,GASKET+PLATE_T)),(WALL,zz(WALL,GASKET+PLATE_T))],
     fill=(18,22,26), outline=(87,211,154), w=0.8)
quad([(0,5),(52,5),(52,26),(0,26)], fill=(18,22,26), outline=(176,108,214), w=0.8)
quad([(WALL,zz(WALL,GASKET+PLATE_T)),(depth-WALL,zz(depth-WALL,GASKET+PLATE_T)),
      (depth-WALL,zz(depth-WALL,GASKET)),(WALL,zz(WALL,GASKET))], fill=(194,204,211))
quad([(WALL+8,zz(WALL+8,POCKET-STAND)),(depth-WALL-8,zz(depth-WALL-8,POCKET-STAND)),
      (depth-WALL-8,zz(depth-WALL-8,POCKET-STAND-PCB_T)),(WALL+8,zz(WALL+8,POCKET-STAND-PCB_T))],
     fill=(29,90,70), outline=(87,211,154), w=0.6)
for u in (WALL+16, depth/2, depth-WALL-16):
    quad([(u-3,zz(u,POCKET)),(u+3,zz(u,POCKET)),(u+3,zz(u,POCKET-STAND)),(u-3,zz(u,POCKET-STAND))], fill=(141,153,162))
for u in (34, depth/2, depth-40):
    quad([(u-1,zz(u,POCKET-STAND-PCB_T)),(u+1,zz(u,POCKET-STAND-PCB_T)),
          (u+1,zz(u,GASKET+PLATE_T)),(u-1,zz(u,GASKET+PLATE_T))], fill=(224,164,88))
quad([(0,7),(WALL+3,7),(WALL+3,14),(0,14)], fill=(176,108,214))
c.text(P(10, 30), "daughterboard pocket", (176,108,214), 9)
c.text(P(depth*0.40, top(depth*0.40)+4), "11 deg — DOE spec", (92,180,222), 12)
c.text(P(depth-2, top(depth)+4), "front 18.0", INK, 10, anchor="ra")
c.text(P(2, top(0)+4), "back 42.1", INK, 10)
fy = c.im.height/SS - 34
c.raw_text((16, fy), "DOE60 case — side section through the centre line, 124.2 mm deep", INK, 11)
c.raw_text((16, fy+15), "flat bottom, top face at 11 deg   |   pocket floor parallel to the plate   |   grey = plate + gasket, green = PCB on 4 mm standoffs", DIM, 9.5)
print("section", c.save("06-case-section.png"))

# ------------------------------------------------------------- 7. case iso
YMAX = b[3]
def zt(y): return FRONT_H + (YMAX - y) * t
CA, SA = math.cos(math.radians(30)), math.sin(math.radians(30))
def iso(x, y, z):
    yp = -y
    return ((x - yp) * CA, (x + yp) * SA - z)
ring = list(CASE_OUT.exterior.coords)[:-1]
prj = [iso(x, y, 0) for x, y in ring]
xs = [p[0] for p in prj+[iso(x,y,zt(y)) for x,y in ring]]
ys = [p[1] for p in prj+[iso(x,y,zt(y)) for x,y in ring]]
c = Canvas((min(xs), min(ys), max(xs), max(ys)), 1800, pad=26, foot=52)
# every side wall, painted far-to-near: on this projection screen depth grows
# with (x - y), so sorting by that and drawing in order hides the back faces.
walls = []
for (x1,y1),(x2,y2) in zip(ring, ring[1:]+ring[:1]):
    depth_key = ((x1 - y1) + (x2 - y2)) / 2.0
    walls.append((depth_key, (x1,y1), (x2,y2)))
walls.sort(key=lambda w: w[0])
for _, (x1,y1), (x2,y2) in walls:
    q = Polygon([iso(x1,y1,0), iso(x2,y2,0), iso(x2,y2,zt(y2)), iso(x1,y1,zt(y1))])
    c.poly(q, fill=(34,41,48), outline=(60,70,80), w=0.6)
top_face = Polygon([iso(x, y, zt(y)) for x, y in ring])
c.poly(top_face, fill=(46,55,64), outline=(92,180,222), w=1.0)
inner_face = Polygon([iso(x, y, zt(y)) for x, y in list(CASE_IN.exterior.coords)[:-1]])
c.poly(inner_face, fill=(120,130,140), outline=(231,236,239), w=0.8)
for k in KEYS:
    if "doe-wkl" not in k["builds"]: continue
    cut = stran2(srot2(sbox(-7,-7,7,7), k["rot"], origin=(0,0)), k["cx"]*U, k["cy"]*U)
    c.poly(Polygon([iso(x, y, zt(y)) for x, y in list(cut.exterior.coords)[:-1]]), fill=(18,22,26))
fy = c.im.height/SS - 32
c.raw_text((16, fy), "DOE60 case — isometric, 335 x 124 mm, 11 deg wedge, plate in place", INK, 11)
c.raw_text((16, fy+15), "front height 18.0 mm, back 42.1 mm   |   isolated top mount on a gasket ledge", DIM, 9.5)
print("iso", c.save("07-case-iso.png"))
