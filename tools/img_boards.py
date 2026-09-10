import sys; sys.path.insert(0, ".")
from img import *
from shapely.ops import unary_union

# ---------------------------------------------------------------- 1. assembly
b = CASE_OUT.bounds
c = Canvas(b, 1900, foot=60)
c.poly(CASE_OUT, fill=(42,50,58), outline=(92,180,222), w=0.9)
c.poly(CASE_IN,  fill=(25,31,36), outline=(92,180,222), w=0.6)
LP, RP = edge_poly("../pcb/DOE60-Left.kicad_pcb"), edge_poly("../pcb/DOE60-Right.kicad_pcb")
for p in (LP, RP):
    c.poly(p, fill=(29,90,70), outline=(87,211,154), w=0.8)
caps, cuts = key_shapes(KEYS)
from img import check_tiling
print('   assembly caps tile, overlap %.1f mm2' % check_tiling([c for c,k in zip(caps,KEYS) if 'doe-wkl' in k['builds']]))
for cap in caps: c.poly(cap, outline=(110,120,130), w=0.5)
for cut in cuts: c.poly(cut, fill=(14,18,22), outline=(194,204,211), w=0.7)
for pcb in ("../pcb/DOE60-Left.kicad_pcb", "../pcb/DOE60-Right.kicad_pcb"):
    for ref, col, shapes, _ in parts(pcb):
        for s in shapes: c.poly(s, fill=col+(230,))
fy = c.im.height/SS - 34
c.raw_text((16, fy), "DOE60  —  case 335 x 124 mm  |  left PCB 157.9 x 105.9  |  right PCB 155.5 x 106.4  |  69 switch positions", INK, 11)
c.raw_text((16, fy+15), "all components on the underside, shown through the board   |   orange = MT9102ET   blue = decoupling   red = SN74LV4051A   purple = 12-way FFC   grey = stabiliser   white = M2", DIM, 9.5)
print("assembly", c.save("01-assembly.png"))

# ------------------------------------------------------------ 2 & 3. halves
for nm, pcb, title in (("02-left.png", "../pcb/DOE60-Left.kicad_pcb", "DOE60-Left   157.9 x 105.9 mm   33 switch positions, 31 mux channels"),
                       ("03-right.png", "../pcb/DOE60-Right.kicad_pcb", "DOE60-Right   155.5 x 106.4 mm   36 switch positions, 32 mux channels")):
    ep = edge_poly(pcb)
    c = Canvas(ep.bounds, 1700, foot=54)
    c.poly(ep, fill=(29,90,70), outline=(87,211,154), w=1.0)
    half = "L" if "Left" in pcb else "R"
    hk = [k for k in KEYS if k["half"] == half]
    caps, cuts = key_shapes(hk)
    for cap in caps: c.poly(cap, outline=(120,150,135), w=0.5)
    for ref, col, shapes, at in parts(pcb):
        for s in shapes: c.poly(s, fill=col+(235,))
        if ref.startswith(("AM","J","MH")):
            c.text((at[0], at[1]-6.5), ref, INK, 8, anchor="ma")
    fy = c.im.height/SS - 34
    c.raw_text((16, fy), title, INK, 11)
    c.raw_text((16, fy+15), "everything on B.Cu, under the switches   |   4x SN74LV4051A   |   one 12-way FFC to the daughterboard   |   4x M2", DIM, 9.5)
    print(nm, c.save(nm))

# ------------------------------------------------------------- 4. daughterboard
ep = edge_poly("../pcb/DOE60-Daughterboard.kicad_pcb")
c = Canvas(ep.bounds, 1500, pad=26, foot=60)
c.poly(ep, fill=(29,90,70), outline=(87,211,154), w=1.2)
for ref, col, shapes, at in parts("../pcb/DOE60-Daughterboard.kicad_pcb"):
    for s in shapes: c.poly(s, fill=col+(240,))
    c.text((at[0], at[1]-7.5), ref, INK, 8.5, anchor="ma")
ux, uy = DB.centroid.x, ep.bounds[1] + 3.5
c.poly(box(ux-4.5, uy-3.75, ux+4.5, uy+3.75), outline=(176,108,214), w=1.0)
c.text((ux, uy+5.5), "USB-C keep-out", (176,108,214), 8, anchor="ma")
fy = c.im.height/SS - 44
c.raw_text((20, fy), "DOE60-Daughterboard   56 x 26 mm", INK, 12)
c.raw_text((20, fy+16), "U1 AT32F405RCT7  |  U2 USBLC6  |  U3/U4 3V3 digital + analog LDOs  |  Y1 12 MHz  |  J2/J3 ribbon to each half", DIM, 9.5)
c.raw_text((20, fy+30), "USB-C receptacle not placed — add Connector:USB_C_Receptacle_HRO_TYPE-C-31-M-12 at the keep-out", (224,164,88), 9.5)
print("daughterboard", c.save("04-daughterboard.png"))
