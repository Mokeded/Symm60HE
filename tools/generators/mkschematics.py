#!/usr/bin/env python3
"""Generate auditable connectivity-capture schematics from the three PCBs.

The boards predate their schematics, so this creates a one-to-one captured
source for every populated pad: reference, value, footprint, pad number and net
all come from the board.  Each net is joined with labels.  Custom symbols use
passive pins so ERC verifies malformed/dangling schematic connectivity without
inventing electrical pin types for the AT32 or the custom Hall footprints.

The output is legacy KiCad 5 syntax because it is compact and deterministic;
`kicad-cli sch upgrade` converts it to the native KiCad 10 `.kicad_sch` files.
"""
from collections import defaultdict
from pathlib import Path
import argparse
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sexp import find, first, loads  # noqa: E402


def prop(fp, name, default=""):
    return next((p[2] for p in find(fp, "property")
                 if len(p) > 2 and p[1] == name), default)


def clean(value):
    return str(value).replace('"', "'").replace("\n", " ")


def symbol_name(ref):
    return "SYM_" + re.sub(r"[^A-Za-z0-9_]", "_", ref)


def components(board_path):
    board = loads(board_path.read_text())
    items = []
    for fp in find(board, "footprint"):
        ref = prop(fp, "Reference")
        if not ref:
            continue
        pads = []
        for pad in find(fp, "pad"):
            net = first(pad, "net")
            if net is not None:
                # Generator-authored boards store `(net "NAME")`; a board
                # resaved by KiCad may store `(net ID "NAME")`.
                net_name = str(net[2] if len(net) > 2 else net[1])
                if net_name:
                    pads.append((str(pad[1]), net_name))
        if not pads:
            continue
        # Several physical pads in the USB-C footprint intentionally share one
        # logical pad number. A schematic symbol must list that pin only once.
        by_number = {}
        for number, net_name in pads:
            if number in by_number and by_number[number] != net_name:
                raise ValueError(f"{ref} pad {number} is assigned to both "
                                 f"{by_number[number]} and {net_name}")
            by_number[number] = net_name
        pads = list(by_number.items())
        pads.sort(key=lambda item: (not item[0].isdigit(),
                                    int(item[0]) if item[0].isdigit() else item[0]))
        items.append({
            "ref": str(ref),
            "value": str(prop(fp, "Value", ref)),
            "footprint": str(fp[1]),
            "pads": pads,
        })
    return sorted(items, key=lambda item: (re.sub(r"\d+$", "", item["ref"]),
                                            int(re.search(r"\d+$", item["ref"]).group())
                                            if re.search(r"\d+$", item["ref"]) else 0,
                                            item["ref"]))


def cache_library(parts, base):
    lines = ["EESchema-LIBRARY Version 2.4", "#encoding utf-8"]
    for item in parts:
        name = symbol_name(item["ref"])
        height = max(300, (len(item["pads"]) - 1) * 100 + 200)
        top = height // 2
        bottom = -top
        prefix = re.sub(r"\d.*$", "", item["ref"]) or "U"
        lines += ["#", f"# {name}", "#",
                  f"DEF {name} {prefix} 0 40 Y Y 1 F N",
                  f'F0 "{prefix}" 0 {top + 120} 50 H V C CNN',
                  f'F1 "{clean(item["value"])}" 0 {bottom - 120} 50 H V C CNN',
                  "DRAW", f"S -900 {top} 900 {bottom} 0 1 10 f"]
        start_y = (len(item["pads"]) - 1) * 50
        for index, (number, net) in enumerate(item["pads"]):
            y = start_y - index * 100
            pin_name = re.sub(r"[^A-Za-z0-9_+\-/]", "_", net)[:24] or "NC"
            lines.append(f"X {pin_name} {number} -1100 {y} 200 R 40 40 1 1 P")
        lines += ["ENDDRAW", "ENDDEF"]
    lines += ["#", "#End Library", ""]
    return "\n".join(lines)


def schematic(parts, base, title):
    nickname = base.replace("-", "_") + "_Cache"
    lines = [
        "EESchema Schematic File Version 4",
        f"LIBS:{base}-cache",
        "EELAYER 29 0", "EELAYER END",
        "$Descr A0 46811 33110", "encoding utf-8", "Sheet 1 1",
        f'Title "{clean(title)} connectivity capture"',
        'Date "2026-09-10"', 'Rev "A"', 'Comp "Symm60HE"',
        'Comment1 "Generated one-to-one from PCB pads; validate against datasheets before prototype"',
        'Comment2 "All custom-symbol pins are passive; ERC is a schematic-integrity gate"',
        'Comment3 "Two-layer 1.2 mm PCB project"', 'Comment4 ""', "$EndDescr",
    ]
    cols = 9
    x_step, y_step = 5000, 3300
    for index, item in enumerate(parts):
        col, row = index % cols, index // cols
        x, y = 2600 + col * x_step, 2200 + row * y_step
        uid = f"{0x70000000 + index:08X}"
        name = symbol_name(item["ref"])
        lines += ["$Comp", f"L {nickname}:{name} {item['ref']}", f"U 1 1 {uid}",
                  f"P {x} {y}",
                  f'F 0 "{item["ref"]}" H {x} {y - 150} 50  0000 C CNN',
                  f'F 1 "{clean(item["value"])}" H {x} {y + 150} 50  0000 C CNN',
                  f'F 2 "{clean(item["footprint"])}" H {x} {y} 50  0001 C CNN',
                  f'F 3 "" H {x} {y} 50  0001 C CNN',
                  f"\t1    {x} {y}", "\t1    0    0    -1", "$EndComp"]
        start_y = (len(item["pads"]) - 1) * 50
        for pin_index, (_, net) in enumerate(item["pads"]):
            # The legacy component transform below mirrors symbol-local Y.
            py = y - start_y + pin_index * 100
            # Extend slightly into the body as well as through the pin's outer
            # endpoint. This remains valid across legacy-library pin-direction
            # interpretation during KiCad 10 import.
            lines += ["Wire Wire Line", f"\t{x - 1450} {py} {x + 1450} {py}",
                      f"Text Label {x - 1450} {py} 0    40   ~ 0", clean(net)]
    lines += ["$EndSCHEMATC", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pcb-dir", type=Path, default=Path("../pcb"))
    args = parser.parse_args()
    for stem in ("Symm60HE-Left", "Symm60HE-Right", "Symm60HE-Daughterboard"):
        board_path = args.pcb_dir / f"{stem}.kicad_pcb"
        parts = components(board_path)
        (args.pcb_dir / f"{stem}-cache.lib").write_text(cache_library(parts, stem))
        (args.pcb_dir / f"{stem}.sch").write_text(schematic(parts, stem, stem))
        print(stem, len(parts), "symbols", sum(len(p["pads"]) for p in parts), "connected pads")
    table = ["(sym_lib_table", "  (version 7)"]
    for stem in ("Symm60HE-Left", "Symm60HE-Right", "Symm60HE-Daughterboard"):
        nickname = stem.replace("-", "_") + "_Cache"
        table.append(f'  (lib (name "{nickname}")(type "Legacy")'
                     f'(uri "${{KIPRJMOD}}/{stem}-cache.lib")'
                     '(options "")(descr "Generated PCB connectivity symbols"))')
    table += [")", ""]
    (args.pcb_dir / "sym-lib-table").write_text("\n".join(table))


if __name__ == "__main__":
    main()
