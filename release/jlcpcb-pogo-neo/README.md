# Symm60HE Neo-pogo BOM and CPL package

This package is generated from the five active boards in `pcb/variants/pogo-neo`. The controller and two floating spring modules under `common/` are used by every build. Choose exactly one folder under `layouts/` for the left and right Hall-PCB assembly files.

Each board directory contains a complete BOM/CPL and a matched `JLCPCB-BOM`/`JLCPCB-CPL` pair. The JLC pair includes the Mill-Max spring and target connector placements by exact manufacturer part number. Their LCSC fields are intentionally blank because no JLC/LCSC selection has been verified. Resolve those lines through Global Sourcing, consignment or a New Parts Request in the component-matching screen. They also remain in `Symm60HE-Neo-Hand-Install-and-Cables.csv` as the fallback until JLC confirms placement.

The four half-board variants prevent mutually exclusive universal-layout sensor positions from being populated together. Do not combine files from different layout folders. Upload each JLCPCB BOM together with the CPL of the identical basename, refresh stock/substitution status, and confirm polarity, pin 1, side and rotation for every line in the placement viewer. The coordinate files come directly from KiCad 10 in millimetres; they do not replace the assembler's visual orientation check.

These files describe assembly only. Gerbers and drills must be regenerated from the same board revisions before ordering. The pogo interface still requires connector-fit, Hall-noise, compression and endurance prototypes.
