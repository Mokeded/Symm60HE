#!/usr/bin/env python3
"""Generate the libhmk Symm60HE target from the released channel maps."""
from collections import defaultdict
from pathlib import Path
import csv
import json

ROOT = Path(__file__).resolve().parent.parent
CHANNELS = ROOT / "Symm60HE-channel-map.csv"
SWITCHES = ROOT / "Symm60HE-switch-map.csv"
ALIASES = ROOT / "Symm60HE-sensor-aliases.csv"
OUT = ROOT / "firmware/libhmk/keyboards/symm60he"
MUX_ORDER = ("AML1", "AML2", "AML3", "AML4", "AMR1", "AMR2", "AMR3", "AMR4")
CHANNEL_PINS = (13, 14, 15, 12, 1, 5, 2, 4)


def key_number(net):
    side, number = net.split("_")[1][0], int(net[-2:])
    return number if side == "L" else 31 + number


def main():
    channels = list(csv.DictReader(CHANNELS.open()))
    switches = list(csv.DictReader(SWITCHES.open()))
    aliases = {row["switch_ref"]: row["sensor_ref"]
               for row in csv.DictReader(ALIASES.open())}
    by_mux_pin = {(row["mux_ref"], int(row["mux_pin"])): key_number(row["channel_net"])
                  for row in channels}
    matrix = [[by_mux_pin.get((mux, pin), 0) for pin in CHANNEL_PINS]
              for mux in MUX_ORDER]

    sensor_to_net = {row["sensor_ref"]: row["channel_net"] for row in channels}
    physical = []
    for sw in switches:
        sensor = aliases.get(sw["ref"], "HE" + sw["ref"][2:])
        net = sensor_to_net[sensor]
        physical.append({**sw, "key": key_number(net) - 1})

    def option(sw):
        builds = set(sw["in_builds"].split())
        if builds == {"wkl", "wklarrows"}:
            return [0, 0]
        if builds == {"wklbs2", "wklbs2arrows"}:
            return [0, 1]
        if builds == {"wkl", "wklbs2"}:
            return [1, 0]
        if builds == {"wklarrows", "wklbs2arrows"}:
            return [1, 1]
        return None

    rows = defaultdict(list)
    for sw in physical:
        rows[round(float(sw["y_mm"]) / 19.05)].append(sw)
    layout = []
    for _, row in sorted(rows.items()):
        entries, previous_right = [], 0.0
        for sw in sorted(row, key=lambda item: float(item["x_mm"])):
            width = float(sw["width_u"])
            left = float(sw["x_mm"]) / 19.05 - width / 2
            entry = {"key": sw["key"]}
            gap = left - previous_right
            if abs(gap) > 0.01:
                entry["x"] = round(gap, 3)
            if width != 1.0:
                entry["w"] = width
            selected = option(sw)
            if selected is not None:
                entry["option"] = selected
            entries.append(entry)
            previous_right = left + width
        layout.append(entries)

    codes = {
        "Esc": "KC_ESC", "!": "KC_1", "@": "KC_2", "#": "KC_3",
        "$": "KC_4", "%": "KC_5", "^": "KC_6", "&": "KC_7",
        "*": "KC_8", "(": "KC_9", ")": "KC_0", "_": "KC_MINS",
        "+": "KC_EQL", "Backspace": "KC_BSPC", "}": "KC_RBRC",
        "Tab": "KC_TAB", "Q": "KC_Q", "W": "KC_W", "E": "KC_E",
        "R": "KC_R", "T": "KC_T", "Y": "KC_Y", "U": "KC_U",
        "I": "KC_I", "O": "KC_O", "P": "KC_P", "{": "KC_LBRC",
        "Backspace/}": "KC_BSLS", "Caps Lock": "KC_CAPS", "A": "KC_A",
        "S": "KC_S", "D": "KC_D", "F": "KC_F", "G": "KC_G",
        "H": "KC_H", "J": "KC_J", "K": "KC_K", "L": "KC_L",
        ":": "KC_SCLN", "Enter": "KC_ENT", "Shift": "KC_LSFT",
        "Z": "KC_Z", "X": "KC_X", "C": "KC_C", "V": "KC_V",
        "B": "KC_B", "N": "KC_N", "M": "KC_M", "<": "KC_COMM",
        ">": "KC_DOT", "Control": "KC_LCTL", "Fn": "MO(1)",
        "Super": "KC_LGUI", "Alt": "KC_LALT", "Space": "KC_SPC",
        "←": "KC_LEFT", "↑": "KC_UP", "→": "KC_RGHT", "↓": "KC_DOWN",
    }
    default = ["KC_NO"] * 63
    for sw in physical:
        # Shared alternate footprints intentionally resolve to one logical key.
        default[sw["key"]] = codes[sw["label"]]
    config = {
        "name": "Symm60HE", "manufacturer": "Mokeded",
        "maintainer": "Symm60HE project",
        "usb": {"vid": "0xAB50", "pid": "0xAB61", "port": "hs"},
        "keyboard": {"num_profiles": 4, "num_layers": 4, "num_keys": 63,
                     "num_advanced_keys": 32},
        "hardware": {"hse_value": 12000000, "driver": "at32f405xx"},
        "analog": {"invert_adc": False, "mux": {
            "select": ["C1", "C2", "C3"],
            "input": ["A3", "A4", "A5", "A6", "A7", "C4", "C5", "B0"],
            "matrix": matrix}},
        "calibration": {"initial_rest_value": 2400,
                        "initial_bottom_out_threshold": 650},
        "layout": {"labels": [["Backspace", "Split 1U", "2U"],
                              ["Bottom corners", "WKL", "Arrows"]],
                   "keymap": layout},
        "keymap": [default, ["_______"] * 63, ["_______"] * 63,
                   ["_______"] * 63],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "keyboard.json").write_text(json.dumps(config, indent=2) + "\n")
    (OUT / "README.md").write_text(
        "# Symm60HE libhmk target\n\n"
        "Generated from the PCB channel map by `tools/mkfirmware.py`. Supports "
        "rapid trigger, adjustable actuation, SOCD/advanced-key bindings, four "
        "profiles, calibration, and the libhmk web configurator.\n")
    print("matrix:", matrix)
    print("layout physical positions:", sum(map(len, layout)), "logical keys: 63")


if __name__ == "__main__":
    main()
