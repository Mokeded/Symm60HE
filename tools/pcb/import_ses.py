#!/usr/bin/env python3
"""Import a Specctra session into a copy of a KiCad PCB."""

import argparse

import wx
import pcbnew


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("session")
    parser.add_argument("output")
    args = parser.parse_args()

    app = wx.App(False)
    board = pcbnew.LoadBoard(args.board)
    if not pcbnew.ImportSpecctraSES(board, args.session):
        raise SystemExit("Specctra session import failed")
    if not pcbnew.SaveBoard(args.output, board):
        raise SystemExit("KiCad board save failed")
    print(args.output)


if __name__ == "__main__":
    main()
