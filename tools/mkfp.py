"""Generate the Symm60HE footprint library.

The Hall-effect key footprints are derived from FN40HE's verified HE1 footprint
so the sensor pads, the two 1.75 mm MX leg holes and the plate cutout outline
are byte-for-byte the shapes that already passed DRC on that board; only the
cap outline on Dwgs.User is rescaled per width.
"""
import re, os, uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Symm60HE_Project.pretty"
# The original generator reached into one developer's FN40HE checkout.  The
# verified 1u derivative is now committed with this project, so it is the
# portable canonical template for every supported key width.
SRC = OUT / "HE_KEY_1.00u.kicad_mod"
U = 19.05
WIDTHS = [1.0, 1.25, 1.5, 1.75, 2.0, 2.25]

tpl = SRC.read_text()

def newid(m):
    return '(uuid "%s")' % uuid.uuid4()

for w in WIDTHS:
    name = "HE_KEY_%.2fu" % w
    s = tpl
    s = re.sub(r'^\(footprint "(?:HE1_MT9102ET_Key_1\.00u|HE_KEY_1\.00u)"',
               '(footprint "%s"' % name, s, count=1)
    s = s.replace('(property "Reference" "HE1"', '(property "Reference" "HE**"')
    s = s.replace('(sheetfile "HE60.kicad_sch")', '(sheetfile "")')
    s = s.replace('(descr "SOT, 3 Pin',
                  '(descr "Symm60HE %gu key: MT9102ET sensor at cap centre, MX leg holes, plate cutout. SOT, 3 Pin' % w)
    # rescale only the cap outline on Dwgs.User
    hw = w * U / 2.0
    def fix(m):
        blk = m.group(0)
        if '(layer "Dwgs.User")' not in blk: return blk
        return re.sub(r'(-?\d+\.?\d*) (-?\d+\.?\d*)',
                      lambda p: "%g %s" % (hw if float(p.group(1)) > 0 else -hw, p.group(2)),
                      blk, count=0)
    s = re.sub(r'\(fp_line\s*\(start [^)]*\)\s*\(end [^)]*\)\s*\(stroke\s*\(width [^)]*\)\s*\(type solid\)\s*\)\s*\(layer "Dwgs\.User"\)\s*\(uuid "[^"]*"\)\s*\)',
               fix, s)
    s = re.sub(r'\(uuid "[0-9a-f-]{36}"\)', newid, s)
    (OUT / (name + ".kicad_mod")).write_text(s)
    print("wrote %s.kicad_mod  (cap %.2f x 19.05 mm)" % (name, w * U))

# --------------------------------------------------------------- mux package --
# FN40HE fits the SN74LV4051A in TSSOP-16.  Here it goes in SOIC-16 instead --
# the same part, SN74LV4051ADR rather than ...APWR.  The reason is routing: a
# 0.65 mm TSSOP leaves 0.25 mm between adjacent pads, so no trace can be taken
# out between them at any sane design rule, and every interior pin has to escape
# by via through a gap its neighbours already own.  SOIC-16's 1.27 mm pitch
# leaves 0.67 mm, which takes a 0.2 mm trace with 0.15 mm either side and turns
# the mux fan-out from impossible into ordinary.  It costs about 30 mm2 per
# package, on boards that have room under the keycaps, and it is easier to hand
# solder.
SOIC = dict(name="AM1_SOIC-16_3.9x9.9mm_P1.27mm",
            pad=(1.95, 0.6), px=2.475, y0=-4.445, pitch=1.27,
            body=(3.9, 9.9), crtyd=(3.7, 5.4))

def soic16():
    s, n = SOIC, SOIC["name"]
    pw, ph = s["pad"]
    bw, bh = s["body"][0]/2, s["body"][1]/2
    cw, ch = s["crtyd"]
    L = ['(footprint "%s"' % n,
         '\t(version 20260206)', '\t(generator "pcbnew")', '\t(generator_version "10.0")',
         '\t(layer "F.Cu")',
         '\t(descr "SOIC, 16 Pin, 1.27 mm pitch, 3.9x9.9 mm body. Symm60HE: SN74LV4051A 8:1 analog mux.")',
         '\t(tags "SOIC SO")',
         '\t(property "Reference" "AM**" (at 0 %.3f 0) (layer "F.SilkS")'
         ' (effects (font (size 1 1) (thickness 0.15))))' % (-ch - 1.0),
         '\t(property "Value" "SN74LV4051A" (at 0 %.3f 0) (layer "F.Fab")'
         ' (effects (font (size 1 1) (thickness 0.15))))' % (ch + 1.0),
         '\t(property "Datasheet" "https://www.ti.com/lit/ds/symlink/sn74lv4051a.pdf"'
         ' (at 0 0 0) (layer "F.Fab") (hide yes)'
         ' (effects (font (size 1.27 1.27) (thickness 0.15))))',
         '\t(property "Description" "8-channel analog multiplexer/demultiplexer"'
         ' (at 0 0 0) (layer "F.Fab") (hide yes)'
         ' (effects (font (size 1.27 1.27) (thickness 0.15))))',
         '\t(sheetname "/")', '\t(sheetfile "")', '\t(attr smd)']
    def line(x1, y1, x2, y2, layer, w):
        return ('\t(fp_line (start %.4f %.4f) (end %.4f %.4f)'
                ' (stroke (width %s) (type solid)) (layer "%s") (uuid "%s"))'
                % (x1, y1, x2, y2, w, layer, uuid.uuid4()))
    for a, b, c, d in ((-cw,-ch, cw,-ch), (cw,-ch, cw,ch), (cw,ch, -cw,ch), (-cw,ch, -cw,-ch)):
        L.append(line(a, b, c, d, "F.CrtYd", 0.05))
    # body on Fab, with the pin-1 corner cut off
    ch1 = 1.0
    for a, b, c, d in ((-bw+ch1,-bh, bw,-bh), (bw,-bh, bw,bh), (bw,bh, -bw,bh),
                       (-bw,bh, -bw,-bh+ch1), (-bw,-bh+ch1, -bw+ch1,-bh)):
        L.append(line(a, b, c, d, "F.Fab", 0.1))
    # silkscreen down the two long sides, clear of the pads, plus a pin-1 dot
    for x in (-bw, bw):
        L.append(line(x, -bh, x, bh, "F.SilkS", 0.12))
    L.append('\t(fp_circle (center %.3f %.3f) (end %.3f %.3f)'
             ' (stroke (width 0.12) (type solid)) (fill yes) (layer "F.SilkS")'
             ' (uuid "%s"))' % (-s["px"] - 0.2, s["y0"], -s["px"] + 0.05, s["y0"], uuid.uuid4()))
    L.append('\t(fp_text user "${REFERENCE}" (at 0 0 0) (layer "F.Fab") (uuid "%s")'
             ' (effects (font (size 1 1) (thickness 0.15))))' % uuid.uuid4())
    for i in range(16):
        if i < 8: x, y = -s["px"], s["y0"] + i * s["pitch"]
        else:     x, y =  s["px"], s["y0"] + (15 - i) * s["pitch"]
        L.append('\t(pad "%d" smd roundrect (at %.4f %.4f) (size %s %s)'
                 ' (layers "F.Cu" "F.Mask" "F.Paste") (roundrect_rratio 0.25)'
                 ' (uuid "%s"))' % (i + 1, x, y, pw, ph, uuid.uuid4()))
    L.append('\t(embedded_fonts no)')
    L.append('\t(model "${KICAD9_3DMODEL_DIR}/Package_SO.3dshapes/SOIC-16_3.9x9.9mm_P1.27mm.step"'
             ' (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))')
    L.append(')')
    (OUT / (n + ".kicad_mod")).write_text("\n".join(L) + "\n")
    print("wrote %s.kicad_mod  (16 pads, %.2f mm pitch, %.2f mm between pads)"
          % (n, s["pitch"], s["pitch"] - ph))

soic16()
