#!/usr/bin/env python3
"""Write native KiCad connectivity-capture schematics from PCB pad data."""
from pathlib import Path
import argparse
import copy
from collections import Counter
import re
import sys
import uuid

from kiutils.items.common import Effects, Font, PageSettings, Position, Property, TitleBlock
from kiutils.items.schitems import (Connection, LocalLabel, NoConnect, SchematicSymbol,
                                    SymbolProjectInstance, SymbolProjectPath)
from kiutils.schematic import Schematic
from kiutils.symbol import Symbol, SymbolLib, SymbolPin

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mkschematics import components, symbol_name  # noqa: E402


def uid():
    return str(uuid.uuid4())


def effect(hidden=False):
    return Effects(font=Font(height=1.0, width=1.0), hide=hidden)


def properties(reference, value, footprint, x=0.0, y=0.0, library=False):
    prefix = re.sub(r"\d.*$", "", reference) or "U"
    return [
        Property("Reference", prefix if library else reference,
                 position=Position(x, y - 2.54, 0), effects=effect()),
        Property("Value", value, position=Position(x, y + 2.54, 0), effects=effect()),
        # The board footprints are project-local generated geometry rather than
        # library-resolved schematic assignments.  Keep that provenance in the
        # description instead of creating a misleading/broken library link.
        Property("Footprint", "", position=Position(x, y, 0), effects=effect(True)),
        Property("Datasheet", "", position=Position(x, y, 0), effects=effect(True)),
        Property("Description", f"PCB-derived connectivity capture; footprint={footprint}",
                 position=Position(x, y, 0), effects=effect(True)),
    ]


def make_schematic(parts, stem):
    sch = Schematic.create_new()
    sch.version = "20260306"
    sch.generator = "eeschema"
    sch.uuid = uid()
    sch.paper = PageSettings("A0")
    sch.titleBlock = TitleBlock(
        title=f"{stem} connectivity capture", date="2026-09-10", revision="A",
        company="Symm60HE",
        comments={1: "Generated one-to-one from PCB connected pads",
                  2: "Custom symbol pins are passive; ERC checks schematic integrity",
                  3: "Validate components and prototype before production"})
    net_uses = Counter(net for item in parts for _, net in item["pads"])
    library_nickname = stem.replace("-", "_") + "_Symbols"
    cols = 9
    for index, item in enumerate(parts):
        name = symbol_name(item["ref"])
        lib_id = f"{library_nickname}:{name}"
        pin_spacing = 2.54
        start_y = 0.0
        pin_defs = []
        for pin_index, (number, net) in enumerate(item["pads"]):
            pin_defs.append(SymbolPin(
                electricalType="passive", graphicalStyle="line",
                position=Position(-10.16, start_y + pin_index * pin_spacing, 0),
                length=2.54, name=net, number=number,
                nameEffects=effect(), numberEffects=effect()))
        body = Symbol(entryName=name, unitId=0, styleId=1)
        unit = Symbol(entryName=name, unitId=1, styleId=1, pins=pin_defs)
        lib = Symbol(libraryNickname=library_nickname, entryName=name,
                     pinNames=True, pinNamesOffset=0.508, inBom=True, onBoard=True,
                     properties=properties(item["ref"], item["value"],
                                           item["footprint"], library=True),
                     units=[body, unit])
        sch.libSymbols.append(lib)

        col, row = index % cols, index // cols
        x, y = 50.8 + col * 124.46, 50.8 + row * 81.28
        symbol_uuid = uid()
        pin_uuids = {number: uid() for number, _ in item["pads"]}
        inst = SchematicSymbol(
            libraryNickname=library_nickname, entryName=name,
            position=Position(x, y, 0), unit=1, inBom=True, onBoard=True,
            dnp=False, uuid=symbol_uuid,
            properties=properties(item["ref"], item["value"],
                                  item["footprint"], x, y),
            pins=pin_uuids,
            instances=[SymbolProjectInstance(
                name=stem,
                paths=[SymbolProjectPath(
                    sheetInstancePath=f"/{sch.uuid}", reference=item["ref"], unit=1)])])
        sch.schematicSymbols.append(inst)
        for pin_index, (_, net) in enumerate(item["pads"]):
            # KiCad symbol-local +Y points upward on the schematic sheet, so
            # the rendered pin location subtracts local Y from the instance Y.
            py = y - start_y - pin_index * pin_spacing
            outer, label_x = x - 10.16, x - 15.24
            if net_uses[net] == 1:
                sch.noConnects.append(NoConnect(position=Position(outer, py), uuid=uid()))
            else:
                sch.graphicalItems.append(Connection(
                    type="wire", points=[Position(outer, py), Position(label_x, py)], uuid=uid()))
                sch.labels.append(LocalLabel(text=net, position=Position(label_x, py, 0),
                                             effects=effect(), uuid=uid()))
    return sch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pcb-dir", type=Path, default=Path("../pcb"))
    parser.add_argument("--stem", action="append",
                        choices=("Symm60HE-Left", "Symm60HE-Right",
                                 "Symm60HE-Daughterboard"),
                        help="regenerate only the selected board; repeat as needed")
    args = parser.parse_args()
    stems = args.stem or ("Symm60HE-Left", "Symm60HE-Right",
                          "Symm60HE-Daughterboard")
    for stem in stems:
        parts = components(args.pcb_dir / f"{stem}.kicad_pcb")
        out = args.pcb_dir / f"{stem}.kicad_sch"
        sch = make_schematic(parts, stem)
        sch.to_file(out)
        external = [copy.deepcopy(symbol) for symbol in sch.libSymbols]
        for symbol in external:
            symbol.libraryNickname = None
        SymbolLib(version="20231120", generator="kicad_symbol_editor",
                  symbols=external).to_file(args.pcb_dir / f"{stem}.kicad_sym")
        print(stem, len(parts), "symbols", sum(len(p["pads"]) for p in parts), "pads")
    table = ["(sym_lib_table", "  (version 7)"]
    for stem in ("Symm60HE-Left", "Symm60HE-Right", "Symm60HE-Daughterboard"):
        nickname = stem.replace("-", "_") + "_Symbols"
        table.append(f'  (lib (name "{nickname}")(type "KiCad")'
                     f'(uri "${{KIPRJMOD}}/{stem}.kicad_sym")'
                     '(options "")(descr "PCB-derived connectivity symbols"))')
    table += [")", ""]
    (args.pcb_dir / "sym-lib-table").write_text("\n".join(table))


if __name__ == "__main__":
    main()
