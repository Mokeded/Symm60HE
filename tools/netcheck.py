"""Net audit: every channel wired once, control and ADC nets consistent."""
import sys, collections
sys.path.insert(0, ".")
from sexp import loads, find, first

def nets(path):
    b = loads(open(path).read())
    m = collections.defaultdict(list)
    for fp in find(b, "footprint"):
        ref = next((p[2] for p in find(fp, "property") if p[1] == "Reference"), "?")
        for p in find(fp, "pad"):
            n = first(p, "net")
            if n: m[n[1]].append("%s.%s" % (ref, p[1]))
    return m

L = nets("../pcb/Symm60HE-Left.kicad_pcb")
R = nets("../pcb/Symm60HE-Right.kicad_pcb")
D = nets("../pcb/Symm60HE-Daughterboard.kicad_pcb")

bad = 0
for half, m, nch in (("L", L, 31), ("R", R, 32)):
    chans = sorted(n for n in m if n.startswith("HE_%s" % half))
    print("%s half: %d channel nets (expected %d)" % (half, len(chans), nch))
    if len(chans) != nch: bad += 1
    for n in chans:
        pins = m[n]
        sens = [p for p in pins if p.startswith("HE")]
        mux  = [p for p in pins if p.startswith("AM")]
        cap  = [p for p in pins if p.startswith("C")]
        if len(mux) != 1 or len(sens) < 1 or len(cap) < 1:
            print("   !! %s: sensors %s mux %s caps %s" % (n, sens, mux, cap)); bad += 1
    for ctl in ("MUX_A0", "MUX_A1", "MUX_A2"):
        pins = m.get(ctl, [])
        muxes = len([p for p in pins if p.startswith("AM")])
        ffc = len([p for p in pins if p.startswith("J")])
        if muxes != 4 or ffc != 1:
            print("   !! %s: %d mux pins, %d ffc pins" % (ctl, muxes, ffc)); bad += 1
    for i in range(1, 5):
        n = "ADC_%s%d" % (half, i)
        pins = m.get(n, [])
        if len(pins) != 2:
            print("   !! %s: %s" % (n, pins)); bad += 1
    print("   +3V3A on %d pads, GND on %d pads" % (len(m.get("+3V3A", [])), len(m.get("GND", []))))

print("\ndaughterboard nets: %s" % ", ".join(sorted(D)))
for half in ("L", "R"):
    for i in range(1, 5):
        n = "ADC_%s%d" % (half, i)
        pins = D.get(n, [])
        if len(pins) != 2 or not any(x.startswith("U1.") for x in pins):
            print("   !! %s should reach the MCU and one FPC connector, got %s" % (n, pins)); bad += 1
missing = [n for n in ("MUX_A0","MUX_A1","MUX_A2","+3V3A") if len(D.get(n,[])) < 3]
if missing: print("   !! not bussed to both halves on the daughterboard: %s" % missing); bad += 1

print("\n%s" % ("NET AUDIT CLEAN" if bad == 0 else "%d net problems" % bad))
