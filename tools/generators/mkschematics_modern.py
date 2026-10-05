#!/usr/bin/env python3
"""Write native KiCad connectivity-capture schematics from PCB pad data."""
from pathlib import Path
import argparse
import copy
from collections import Counter
import os
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


def properties(reference, value, footprint, x=0.0, y=0.0, library=False,
               assign_footprint=False):
    prefix = re.sub(r"\d.*$", "", reference) or "U"
    return [
        Property("Reference", prefix if library else reference,
                 position=Position(x, y - 2.54, 0), effects=effect()),
        Property("Value", value, position=Position(x, y + 2.54, 0), effects=effect()),
        # Standalone connectivity captures retain provenance only. Combined
        # panel projects opt into the real library assignment so schematic-led
        # edits can update their already-matched panel footprints.
        Property("Footprint", ((footprint if ":" in footprint else
                                f"Symm60HE_Project:{footprint}")
                               if assign_footprint else ""),
                 position=Position(x, y, 0), effects=effect(True)),
        Property("Datasheet", "", position=Position(x, y, 0), effects=effect(True)),
        Property("Description", f"PCB-derived connectivity capture; footprint={footprint}",
                 position=Position(x, y, 0), effects=effect(True)),
    ]


def make_schematic(parts, stem, assign_footprints=False):
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
    # A combined two-half panel has roughly twice the symbols of one master
    # board.  Pack those projects across the A0 sheet so the full electrical
    # design remains on-page and readable instead of extending several metres
    # below the title block.
    combined = len(parts) > 220
    cols = 22 if combined else 9
    x_step = 50.8 if combined else 124.46
    y_step = 45.72 if combined else 81.28
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
                                           item["footprint"], library=True,
                                           assign_footprint=assign_footprints),
                     units=[body, unit])
        sch.libSymbols.append(lib)

        col, row = index % cols, index // cols
        x, y = 50.8 + col * x_step, 50.8 + row * y_step
        symbol_uuid = uid()
        pin_uuids = {number: uid() for number, _ in item["pads"]}
        inst = SchematicSymbol(
            libraryNickname=library_nickname, entryName=name,
            position=Position(x, y, 0), unit=1, inBom=True, onBoard=True,
            dnp=False, uuid=symbol_uuid,
            properties=properties(item["ref"], item["value"],
                                  item["footprint"], x, y,
                                  assign_footprint=assign_footprints),
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


def write_symbol_library_table(directory):
    """Keep every generated symbol library in this project directory visible."""
    directory = Path(directory)
    table = ["(sym_lib_table", "  (version 7)"]
    for library in sorted(directory.glob("*.kicad_sym")):
        if library.name.startswith("._"):
            continue
        stem = library.stem
        nickname = stem.replace("-", "_") + "_Symbols"
        table.append(f'  (lib (name "{nickname}")(type "KiCad")'
                     f'(uri "${{KIPRJMOD}}/{library.name}")'
                     '(options "")(descr "PCB-derived connectivity symbols"))')
    table += [")", ""]
    (directory / "sym-lib-table").write_text("\n".join(table))


def write_footprint_library_table(directory):
    """Point a nested combined project at the repository footprint library."""
    directory = Path(directory).resolve()
    library = next((parent / "Symm60HE_Project.pretty"
                    for parent in (directory, *directory.parents)
                    if (parent / "Symm60HE_Project.pretty").is_dir()), None)
    if library is None:
        raise FileNotFoundError("Symm60HE_Project.pretty not found above " +
                                str(directory))
    relative = Path(os.path.relpath(library, directory)).as_posix()
    text = ("(fp_lib_table\n"
            "  (lib (name \"Symm60HE_Project\")(type \"KiCad\")"
            f"(uri \"${{KIPRJMOD}}/{relative}\")(options \"\")"
            "(descr \"Symm60HE split-PCB footprints\"))\n"
            ")\n")
    (directory / "fp-lib-table").write_text(text)


def write_schematic_for_board(board_path, out_path=None,
                              assign_footprints=False):
    """Write a native schematic and symbol audit library for any PCB."""
    board_path = Path(board_path)
    out_path = Path(out_path or board_path.with_suffix(".kicad_sch"))
    stem = out_path.stem
    parts = components(board_path)
    sch = make_schematic(parts, stem, assign_footprints=assign_footprints)
    sch.to_file(out_path)
    external = [copy.deepcopy(symbol) for symbol in sch.libSymbols]
    for symbol in external:
        symbol.libraryNickname = None
    SymbolLib(version="20231120", generator="kicad_symbol_editor",
              symbols=external).to_file(out_path.with_suffix(".kicad_sym"))
    write_symbol_library_table(out_path.parent)
    write_footprint_library_table(out_path.parent)
    return sch.uuid, len(parts), sum(len(part["pads"]) for part in parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pcb-dir", type=Path, default=Path("../pcb"))
    parser.add_argument("--stem", action="append",
                        help="regenerate only the selected board; repeat as needed")
    args = parser.parse_args()
    stems = args.stem or ("Symm60HE-Left", "Symm60HE-Right",
                          "Symm60HE-Daughterboard")
    for stem in stems:
        _, count, pads = write_schematic_for_board(
            args.pcb_dir / f"{stem}.kicad_pcb",
            args.pcb_dir / f"{stem}.kicad_sch")
        print(stem, count, "symbols", pads, "pads")
    write_symbol_library_table(args.pcb_dir)


if __name__ == "__main__":
    main()
