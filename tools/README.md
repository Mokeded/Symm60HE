# Tooling

The project tools are grouped by the artifact or workflow they maintain. Run
the complete, supported pipeline from the repository root with:

```sh
./build.sh
```

`build.sh` sets `PYTHONPATH` so category scripts can share the parsers and
geometry libraries kept in this directory. For an individual command, use the
same convention from the repository root, for example:

```sh
PYTHONPATH=tools .venv/bin/python tools/layouts/verify_layout_pcbs.py
```

## Folders

| Folder | Purpose |
| --- | --- |
| [`cad/`](cad/) | Fusion 360 reference preparation, FreeCAD export, and mechanical verification |
| [`generators/`](generators/) | Firmware and schematic source generation |
| [`layouts/`](layouts/) | Fixed-layout derivation, materialization, and layout verification |
| [`pcb/`](pcb/) | PCB editing, routing repair, panelization, and fabrication-preparation commands |
| [`pogo/`](pogo/) | Pogo/ribbon prototype generation, panelization, and verification |
| [`releases/`](releases/) | Manufacturing package creation and checksums |
| [`rendering/`](rendering/) | PCB, plate, CAD, and gallery image generation |

The Python files directly in `tools/` are shared libraries, source generators
used by several workflows, or top-level checks. The main verification entry
point is [`verify.py`](verify.py).

Do not run PCB mutation commands casually against the routed masters. The
supported way to regenerate release artifacts is the repository-level
`build.sh`, which applies the operations in their validated order.
