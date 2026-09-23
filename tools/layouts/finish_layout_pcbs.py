#!/usr/bin/env python3
"""Refill, locally repair, prune, and report layout-specific PCB routing."""
from __future__ import annotations

import argparse
import glob
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
PYTHON = Path(os.environ.get("SYMM60_PYTHON", ROOT / ".venv/bin/python"))


def find_kicad_cli():
    found = shutil.which("kicad-cli")
    if found:
        return found
    candidates = sorted(glob.glob(
        "/opt/homebrew/Caskroom/kicad/*/KiCad/KiCad.app/Contents/MacOS/kicad-cli"),
        reverse=True)
    if not candidates:
        raise RuntimeError("kicad-cli not found")
    return candidates[0]


def run(command, env=None):
    subprocess.run(command, check=True, cwd=ROOT, env=env,
                   stdout=subprocess.DEVNULL)


def drc(cli, board, report):
    subprocess.run([cli, "pcb", "drc", "--refill-zones", "--save-board",
                    "--severity-all", "--format", "report", "--output",
                    str(report), str(board)], cwd=ROOT, check=False,
                   stdout=subprocess.DEVNULL)


ERRORS = ("clearance", "shorting_items", "tracks_crossing",
          "connection_width", "track_dangling", "via_dangling",
          "unconnected_items", "holes_co_located", "hole_to_hole",
          "hole_clearance", "track_not_centered_on_via", "solder_mask_bridge")


def count(report, categories):
    pattern = re.compile(r"^\[(" + "|".join(map(re.escape, categories)) + r")\]")
    return sum(bool(pattern.match(line))
               for line in report.read_text().splitlines())


def score(report):
    """How bad the board is, worst first.

    Shorts and crossings rank ahead of the total so that no repair can trade
    them for a handful of lesser findings: giving a net its old copper back can
    drop it straight through whatever was routed into that space meanwhile, and
    that is never an improvement however many clearances it settles.
    """
    return (count(report, ("shorting_items", "tracks_crossing")),
            count(report, ("unconnected_items",)),
            count(report, ERRORS))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path,
                        default=ROOT / "pcb/variants/layouts")
    parser.add_argument("--board", type=Path, action="append")
    args = parser.parse_args()
    cli = find_kicad_cli()
    boards = args.board or sorted(args.root.glob("*/*.kicad_pcb"))

    for board in boards:
        report = board.with_name(board.stem + "-drc.rpt")
        run([str(PYTHON), str(TOOLS / "layouts/clear_variant_led_apertures.py"),
             str(board), str(board)])
        # Dropping this layout's unused switches leaves nets with one pad or
        # none; their copper cannot connect anything and only comes back as a
        # dangling run in every later report.
        run([str(PYTHON), str(TOOLS / "pcb/drop_orphan_copper.py"), str(board),
             str(board)])
        drc(cli, board, report)

        # Route ordinary opens first, then the GND open that may have been
        # created when copper crossing a moved aperture was removed.
        run([str(PYTHON), str(TOOLS / "pcb/repair_open_routes.py"), str(board),
             str(report), str(board), "--step", "0.25"])
        drc(cli, board, report)
        ground_env = os.environ.copy()
        ground_env["SYMM60_ROUTE_GND"] = "1"
        run([str(PYTHON), str(TOOLS / "pcb/repair_open_routes.py"), str(board),
             str(report), str(board), "--step", "0.25"], env=ground_env)

        # Deleted layout-only parts leave harmless but DRC-visible route
        # tails.  Remove only the exact objects named by KiCad, iterating as a
        # longer tail exposes its next leaf.
        for _ in range(16):
            drc(cli, board, report)
            dangling = count(report, ("track_dangling", "via_dangling"))
            if not dangling:
                break
            run([str(PYTHON), str(TOOLS / "pcb/prune_dangling.py"), str(board),
                 str(report), str(board), "--skip-missing"])
        drc(cli, board, report)
        if count(report, ("unconnected_items",)):
            run([str(PYTHON), str(TOOLS / "pcb/add_filtered_ground_stitches.py"),
                 str(board), str(board)])
            drc(cli, board, report)
        # Joining a pour or clearing a window can strand the copper that used
        # to feed it, so sweep the leaves once more before reporting.  The
        # report has to be refreshed first: prune_dangling resolves the exact
        # items KiCad named, and the previous step may have moved them.
        for _ in range(8):
            drc(cli, board, report)
            if not count(report, ("track_dangling", "via_dangling")):
                break
            run([str(PYTHON), str(TOOLS / "pcb/prune_dangling.py"), str(board),
                 str(report), str(board), "--skip-missing"])
        run([str(PYTHON), str(TOOLS / "pcb/tidy_via_joints.py"), str(board),
             str(board), "--report", str(report)])
        drc(cli, board, report)

        errors = count(report, ("clearance", "shorting_items", "tracks_crossing",
                                "connection_width", "track_dangling",
                                "via_dangling", "unconnected_items"))
        if errors:
            # The restored fixed-layout LED positions open corridors that are
            # sampled poorly by the historical grid origin.  A half-cell
            # retry finds the same legal local routes deterministically.
            retry_env = os.environ.copy()
            retry_env["SYMM60_GRID_OFFSET_X"] = "0.125"
            retry_env["SYMM60_GRID_OFFSET_Y"] = "0.125"
            run([str(PYTHON), str(TOOLS / "pcb/repair_open_routes.py"), str(board),
                 str(report), str(board), "--step", "0.25"], env=retry_env)
            drc(cli, board, report)
            retry_env["SYMM60_ROUTE_GND"] = "1"
            run([str(PYTHON), str(TOOLS / "pcb/repair_open_routes.py"), str(board),
                 str(report), str(board), "--step", "0.25"], env=retry_env)
            drc(cli, board, report)

        run([str(PYTHON), str(TOOLS / "layouts/fix_fixed_led_routes.py"), str(board),
             str(board)])
        for _ in range(8):
            drc(cli, board, report)
            if not count(report, ("track_dangling", "via_dangling")):
                break
            run([str(PYTHON), str(TOOLS / "pcb/prune_dangling.py"), str(board),
                 str(report), str(board), "--skip-missing"])
        # Grid retries may converge on a pre-existing same-net via.  Remove
        # only byte-equivalent co-located vias before the authoritative DRC;
        # non-equivalent collisions remain errors in dedupe_vias.py.
        run([str(PYTHON), str(TOOLS / "pcb/dedupe_vias.py"), str(board),
             str(board)])
        drc(cli, board, report)

        # What is left now is mechanical rather than electrical: copper the
        # layout's own drills, edges or neighbours leave no room for.  Each
        # pass gives one class of finding somewhere to move to and routes it
        # again, and every pass is a transaction -- a board that comes out
        # worse is rolled back, and a net that could not be re-routed keeps
        # the copper it had.
        def attempt(name, categories, rip):
            before = score(report)
            if not count(report, categories):
                return
            backup = board.with_suffix(".bak")
            shutil.copy2(board, backup)
            run(rip)
            drc(cli, board, report)
            run([str(PYTHON), str(TOOLS / "pcb/repair_open_routes.py"),
                 str(board), str(report), str(board), "--step", "0.25"])
            drc(cli, board, report)
            run([str(PYTHON), str(TOOLS / "pcb/repair_open_routes.py"),
                 str(board), str(report), str(board), "--step", "0.25"],
                env=ground_env)
            drc(cli, board, report)
            run([str(PYTHON), str(TOOLS / "pcb/restore_open_nets.py"),
                 str(board), str(backup), str(report), str(board)])
            for _ in range(8):
                drc(cli, board, report)
                if not count(report, ("track_dangling", "via_dangling")):
                    break
                run([str(PYTHON), str(TOOLS / "pcb/prune_dangling.py"),
                     str(board), str(report), str(board), "--skip-missing"])
            run([str(PYTHON), str(TOOLS / "pcb/tidy_via_joints.py"), str(board),
                 str(board), "--report", str(report)])
            run([str(PYTHON), str(TOOLS / "pcb/dedupe_vias.py"), str(board),
                 str(board)])
            drc(cli, board, report)
            if score(report) > before:
                shutil.copy2(backup, board)
                drc(cli, board, report)
            backup.unlink()

        for _ in range(3):
            worst = score(report)
            attempt("opens", ("unconnected_items",),
                    [str(PYTHON), str(TOOLS / "pcb/join_ground_islands.py"),
                     str(board), str(board)])
            attempt("walled-in opens", ("unconnected_items",),
                    [str(PYTHON), str(TOOLS / "pcb/rip_around_open.py"),
                     str(board), str(report), str(board)])
            attempt("drilled-through copper",
                    ("hole_clearance", "copper_edge_clearance"),
                    [str(PYTHON), str(TOOLS / "pcb/rip_around_holes.py"),
                     str(board), str(report), str(board), "--radius", "1.8"])
            attempt("tight gaps", ("clearance", "shorting_items",
                                   "tracks_crossing"),
                    [str(PYTHON), str(TOOLS / "pcb/rip_rule_offenders.py"),
                     str(board), str(report), str(board), "--shorter-only",
                     "--category", "clearance", "--category", "shorting_items",
                     "--category", "tracks_crossing"])
            run([str(PYTHON), str(TOOLS / "pcb/tidy_via_joints.py"), str(board),
                 str(board), "--report", str(report)])
            drc(cli, board, report)
            # A gap short by a few microns is a nudge, not a re-route: on a
            # board this full the router puts a ripped trace back exactly where
            # it was, so bend it a hair clear instead.
            for _ in range(3):
                if not count(report, ("clearance", "hole_clearance",
                                      "copper_edge_clearance")):
                    break
                run([str(PYTHON), str(TOOLS / "pcb/nudge_clearance.py"),
                     str(board), str(report), str(board)])
                drc(cli, board, report)
            if score(report) >= worst:
                break

        errors = count(report, ERRORS)
        edge = count(report, ("copper_edge_clearance",))
        print(f"{board.parent.name}/{board.name}: {errors} routing/connectivity "
              f"errors; {edge} copper-edge warning(s)")


if __name__ == "__main__":
    main()
