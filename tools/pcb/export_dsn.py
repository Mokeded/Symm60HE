#!/usr/bin/env python3
"""Export a KiCad board to Specctra DSN with the bundled pcbnew API."""

import argparse

import wx
import pcbnew


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("output")
    args = parser.parse_args()

    app = wx.App(False)
    board = pcbnew.LoadBoard(args.board)
    if not pcbnew.ExportSpecctraDSN(board, args.output):
        raise SystemExit("Specctra export failed")
    print(args.output)


if __name__ == "__main__":
    main()
