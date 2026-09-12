"""Switch geometry for the Symm60HE split PCBs.

Reads the published KLE builds, unions their key positions so one PCB carries
every layout option, converts to millimetres, and splits into halves.
"""
import csv, json, math, os

U = 19.05
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KLE = os.environ.get("SYMM60HE_KLE_DIR", os.path.join(ROOT, "layout", "kle"))
SWITCH_MAP = os.path.join(ROOT, "Symm60HE-switch-map.csv")
BUILDS = ["doe-wkl", "doe-wklbs2", "doe-wklarrows", "doe-wklbs2arrows"]

def parse(path):
    """-> list of (label, cx, cy, rot_deg, w) in KLE units, centre of the cap."""
    data = json.load(open(path))
    cur = dict(x=0.0, y=0.0, rx=0.0, ry=0.0, r=0.0)
    w = 1.0
    out = []
    for row in data:
        for it in row:
            if isinstance(it, str):
                # centre in the rotated frame, then rotate about (rx, ry)
                cx, cy = cur["x"] + w / 2.0, cur["y"] + 0.5
                a = math.radians(cur["r"]); ox, oy = cur["rx"], cur["ry"]
                gx = ox + (cx - ox) * math.cos(a) - (cy - oy) * math.sin(a)
                gy = oy + (cx - ox) * math.sin(a) + (cy - oy) * math.cos(a)
                out.append((it.split("\n")[0], gx, gy, cur["r"], w))
                cur["x"] += w; w = 1.0
            else:
                for k in ("r", "rx", "ry"):
                    if k in it:
                        cur[k] = it[k]
                        if k == "rx": cur["x"] = it[k]
                        if k == "ry": cur["y"] = it[k]
                if "x" in it: cur["x"] += it["x"]
                if "y" in it: cur["y"] += it["y"]
                w = it.get("w", 1.0)
        cur["y"] += 1.0; cur["x"] = cur["rx"]
    return out

def collect():
    paths = [os.path.join(KLE, b + ".kle.json") for b in BUILDS]
    if not all(os.path.exists(path) for path in paths):
        if not os.path.exists(SWITCH_MAP):
            missing = [path for path in paths if not os.path.exists(path)]
            raise FileNotFoundError(
                "layout inputs are missing; expected the committed switch map at %s "
                "or all KLE files under %s (missing: %s)"
                % (SWITCH_MAP, KLE, ", ".join(missing)))
        keys = []
        with open(SWITCH_MAP, newline="") as f:
            for row in csv.DictReader(f):
                builds = {"doe-" + name for name in row["in_builds"].split()}
                labels = set(row["label"].split("/"))
                keys.append(dict(label=row["label"],
                                 cx=float(row["x_mm"]) / U,
                                 cy=float(row["y_mm"]) / U,
                                 rot=-float(row["rotation_deg"]),
                                 w=float(row["width_u"]),
                                 labels=labels, builds=builds))
        return keys

    seen, keys = {}, []
    for b in BUILDS:
        for lab, cx, cy, rot, w in parse(os.path.join(KLE, b + ".kle.json")):
            # a switch position is defined by where it sits and how wide the cap
            # is -- the same centre with a different width is a different cell
            k = (round(cx, 3), round(cy, 3), round(w, 3))
            if k in seen:
                seen[k]["labels"].add(lab)
                seen[k]["builds"].add(b)
                continue
            e = dict(label=lab, cx=cx, cy=cy, rot=rot, w=w,
                     labels={lab}, builds={b})
            seen[k] = e; keys.append(e)
    return keys

KEYS = collect()
xs = [k["cx"] for k in KEYS]
AXIS = (min(xs) + max(xs)) / 2.0
for k in KEYS:
    k["half"] = "L" if k["cx"] < AXIS else "R"

if __name__ == "__main__":
    import csv, sys
    L = [k for k in KEYS if k["half"] == "L"]
    R = [k for k in KEYS if k["half"] == "R"]
    print("switch positions: %d total  (%d left, %d right)" % (len(KEYS), len(L), len(R)))
    for half, ks in (("L", L), ("R", R)):
        by_w = {}
        for k in ks: by_w[k["w"]] = by_w.get(k["w"], 0) + 1
        print("  %s widths: %s" % (half, ", ".join("%gu x%d" % (w, n) for w, n in sorted(by_w.items()))))
    ys = [k["cy"] for k in KEYS]
    print("extent: x %.2f..%.2f u, y %.2f..%.2f u  (%.1f x %.1f mm)"
          % (min(xs), max(xs), min(ys), max(ys),
             (max(xs) - min(xs)) * U, (max(ys) - min(ys)) * U))
    with open("../Symm60HE-switch-map.csv", "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["ref", "half", "label", "x_mm", "y_mm", "rotation_deg", "width_u", "in_builds"])
        n = {"L": 0, "R": 0}
        for k in sorted(KEYS, key=lambda k: (k["half"], round(k["cy"], 2), k["cx"])):
            n[k["half"]] += 1
            wr.writerow([("SWL%d" if k["half"] == "L" else "SWR%d") % n[k["half"]],
                         k["half"], "/".join(sorted(k["labels"])),
                         round(k["cx"] * U, 3), round(k["cy"] * U, 3),
                         round(-k["rot"], 3), k["w"],
                         " ".join(sorted(b.replace("doe-", "") for b in k["builds"]))])
    print("wrote Symm60HE-switch-map.csv")
