"""Project files, maps and BOM."""
import json, csv, sys, os, shutil
sys.path.insert(0, ".")
from sexp import loads, find, first

TEMPLATE = "../pcb/Symm60HE-Left.kicad_pro"
if not os.path.exists(TEMPLATE):
    raise FileNotFoundError("missing committed KiCad project template: " + TEMPLATE)
PRO = json.load(open(TEMPLATE))
for name in ("Symm60HE-Left", "Symm60HE-Right", "Symm60HE-Daughterboard"):
    p = json.loads(json.dumps(PRO))
    p["meta"]["filename"] = name + ".kicad_pro"
    for k in ("sheets", "text_variables"):
        p.pop(k, None)
    p["sheets"] = [["00000000-0000-0000-0000-000000000000", "Root"]]
    p["board"]["design_settings"]["defaults"] = p["board"]["design_settings"].get("defaults", {})
    for cls in p["net_settings"]["classes"]:
        if cls["name"] == "Default":
            cls["track_width"] = 0.2
            cls["diff_pair_width"] = 0.2
            cls["clearance"] = 0.15
            cls["via_diameter"] = 0.6
            cls["via_drill"] = 0.3
    json.dump(p, open("../pcb/%s.kicad_pro" % name, "w"), indent=2)
print("wrote 3 .kicad_pro files")
shutil.copyfile("../fp-lib-table", "../pcb/fp-lib-table")
print("wrote pcb/fp-lib-table")

# channel map
rows = []
for name, half in (("Symm60HE-Left", "L"), ("Symm60HE-Right", "R")):
    b = loads(open("../pcb/%s.kicad_pcb" % name).read())
    sens, mux = {}, {}
    for fp in find(b, "footprint"):
        ref = next((q[2] for q in find(fp, "property") if q[1] == "Reference"), "")
        val = next((q[2] for q in find(fp, "property") if q[1] == "Value"), "")
        at = first(fp, "at")
        for p in find(fp, "pad"):
            n = first(p, "net")
            if not n or not n[1].startswith("HE_"): continue
            if ref.startswith("HE"):
                sens.setdefault(n[1], []).append((ref, float(at[1]), float(at[2]),
                                                  float(at[3]) if len(at) > 3 else 0.0))
            elif ref.startswith("AM"):
                mux[n[1]] = (ref, p[1])
    for net in sorted(sens, key=lambda s: int(s[4:])):
        for ref, x, y, r in sens[net]:
            m = mux.get(net, ("", ""))
            rows.append([half, net, ref, m[0], m[1], round(x, 3), round(y, 3), round(r, 2)])
with open("../Symm60HE-channel-map.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["half", "channel_net", "sensor_ref", "mux_ref", "mux_pin", "x_mm", "y_mm", "rot_deg"])
    w.writerows(rows)
print("wrote Symm60HE-channel-map.csv (%d sensor rows)" % len(rows))

# ribbon pinout
RIB = ["+3V3A", "GND", "MUX_A0", "MUX_A1", "MUX_A2", "GND",
       "ADC_x1", "GND", "ADC_x2", "GND", "ADC_x3", "ADC_x4"]
with open("../Symm60HE-ribbon-pinout.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["pin", "net", "direction", "notes"])
    for i, n in enumerate(RIB, 1):
        d = {"+3V3A": "daughterboard -> half", "GND": "common",
             "MUX_A0": "daughterboard -> half", "MUX_A1": "daughterboard -> half",
             "MUX_A2": "daughterboard -> half"}.get(n, "half -> daughterboard")
        note = ("analog, keep the adjacent ground" if n.startswith("ADC") else
                "analog rail, from the XC6206" if n == "+3V3A" else
                "mux address, shared by both halves" if n.startswith("MUX") else "")
        w.writerow([i, n, d, note])
print("wrote Symm60HE-ribbon-pinout.csv (12 way, 1.0 mm FPC)")
