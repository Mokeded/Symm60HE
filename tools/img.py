"""Raster images of the real geometry, drawn with PIL at 3x and downsampled."""
import sys, math, os, itertools
sys.path.insert(0, ".")
from PIL import Image, ImageDraw, ImageFont
from sexp import loads, find, first
from shapely.geometry import Polygon, box, Point
from shapely.affinity import rotate as srot, translate as stran
from geom import KEYS, U
from outline import CASE_OUT, CASE_IN, LEFT_PCB, RIGHT_PCB, DB, axis_mm

SS = 3
BG, INK, DIM = (18, 22, 26), (231, 236, 239), (141, 153, 162)
os.makedirs("../docs/img", exist_ok=True)

def font(sz):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(p):
            try: return ImageFont.truetype(p, sz)
            except Exception: pass
    return ImageFont.load_default()

class Canvas:
    def __init__(self, bounds, width=1600, pad=18, foot=52):
        x0, y0, x1, y1 = bounds
        width = width * SS                      # `width` is the final pixel width
        self.s = (width - 2*pad*SS) / ((x1-x0) or 1)
        self.x0, self.y0, self.pad = x0, y0, pad*SS
        h = int((y1-y0)*self.s) + 2*self.pad + foot*SS
        self.im = Image.new("RGB", (int(width), h), BG)
        self.d = ImageDraw.Draw(self.im, "RGBA")
    def p(self, xy):
        return (self.pad + (xy[0]-self.x0)*self.s, self.pad + (xy[1]-self.y0)*self.s)
    def poly(self, poly, fill=None, outline=None, w=1.0):
        if poly.is_empty: return
        geoms = poly.geoms if hasattr(poly, "geoms") else [poly]
        for g in geoms:
            pts = [self.p(c) for c in g.exterior.coords]
            if fill: self.d.polygon(pts, fill=fill)
            if outline: self.d.line(pts, fill=outline, width=max(1, int(w*SS)))
            for r in g.interiors:
                ip = [self.p(c) for c in r.coords]
                if fill: self.d.polygon(ip, fill=BG)
                if outline: self.d.line(ip, fill=outline, width=max(1, int(w*SS)))
    def text(self, xy, s, col=DIM, sz=11, anchor="la"):
        self.d.text(self.p(xy), s, fill=col, font=font(int(sz*SS)), anchor=anchor)
    def raw_text(self, xy, s, col=DIM, sz=11, anchor="la"):
        self.d.text((xy[0]*SS, xy[1]*SS), s, fill=col, font=font(int(sz*SS)), anchor=anchor)
    def save(self, name):
        out = self.im.resize((self.im.width//SS, self.im.height//SS), Image.LANCZOS)
        out.save("../docs/img/" + name)
        return out.size

def check_tiling(caps, label="key outlines"):
    """Guard: the caps must tile.  Rotating them the wrong way multiplies the
    overlap about six-fold, which is how this bug reached the images once."""
    ov = sum(a.intersection(b).area for a, b in itertools.combinations(caps, 2))
    assert ov < 40.0, "%s do not tile: %.1f mm2 of overlap" % (label, ov)
    return ov

def key_shapes(keys):
    caps, cuts = [], []
    for k in keys:
        w = k["w"]*U
        # KLE r is a standard-matrix rotation in a y-down frame, so it applies
        # as +r here.  The KiCad boards store -r because KiCad's `at` angle is
        # counter-clockwise-positive on screen; parts() undoes that with -angle.
        caps.append(stran(srot(box(-w/2, -9.525, w/2, 9.525), k["rot"], origin=(0,0)), k["cx"]*U, k["cy"]*U))
        cuts.append(stran(srot(box(-7, -7, 7, 7), k["rot"], origin=(0,0)), k["cx"]*U, k["cy"]*U))
    return caps, cuts

COL = {"HE": (224,164,88), "C": (92,180,222), "AM": (224,92,92), "J": (176,108,214),
       "S": (141,153,162), "MH": (231,236,239), "U": (224,92,92), "Y": (87,211,154),
       "F": (87,211,154), "SW": (176,108,214), "R": (92,180,222)}
def parts(pcb):
    b = loads(open(pcb).read())
    out = []
    for fp in find(b, "footprint"):
        ref = next((q[2] for q in find(fp,"property") if q[1]=="Reference"), "")
        at = first(fp,"at"); x, y = float(at[1]), float(at[2])
        r = float(at[3]) if len(at) > 3 else 0.0
        shapes = []
        for p in find(fp,"pad"):
            a = first(p,"at"); sz = first(p,"size")
            px, py = float(a[1]), float(a[2]); pw, ph = float(sz[1]), float(sz[2])
            s = Point(px,py).buffer(pw/2) if p[3]=="circle" else box(px-pw/2, py-ph/2, px+pw/2, py+ph/2)
            shapes.append(stran(srot(s, -r, origin=(0,0)), x, y))
        pre = "".join(c for c in ref[:2] if not c.isdigit())
        out.append((ref, COL.get(pre, COL.get(ref[:1], (136,136,136))), shapes, (x,y)))
    return out

def edge_poly(pcb):
    b = loads(open(pcb).read())
    segs = [(( float(first(l,"start")[1]), float(first(l,"start")[2])),
             ( float(first(l,"end")[1]),   float(first(l,"end")[2])))
            for l in find(b,"gr_line") if first(l,"layer")[1]=="Edge.Cuts"]
    return Polygon([segs[0][0]] + [s[1] for s in segs])
