"""Generate the Symm60HE footprint library.

The Hall-effect key footprints are derived from FN40HE's verified HE1 footprint
so the sensor pads, the two 1.75 mm MX leg holes and the plate cutout outline
are byte-for-byte the shapes that already passed DRC on that board; only the
cap outline on Dwgs.User is rescaled per width.
"""
import re, os, uuid

SRC = "/home/user/FN40HE/FN40_Project.pretty/HE1_MT9102ET_Key_1.00u.kicad_mod"
OUT = "../Symm60HE_Project.pretty"
U = 19.05
WIDTHS = [1.0, 1.25, 1.5, 1.75, 2.0, 2.25]

tpl = open(SRC).read()

def newid(m):
    return '(uuid "%s")' % uuid.uuid4()

for w in WIDTHS:
    name = "HE_KEY_%.2fu" % w
    s = tpl
    s = s.replace('(footprint "HE1_MT9102ET_Key_1.00u"', '(footprint "%s"' % name)
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
    open(os.path.join(OUT, name + ".kicad_mod"), "w").write(s)
    print("wrote %s.kicad_mod  (cap %.2f x 19.05 mm)" % (name, w * U))
