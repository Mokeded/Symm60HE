#!/usr/bin/env python3
"""Re-enable every ignored PCB rule in temporary projects and report results."""
from collections import Counter
from pathlib import Path
import json
import re
import shutil
import subprocess
import tempfile

from verify import BOARDS, ROOT, find_kicad_cli


def main():
    cli = find_kicad_cli()
    if not cli:
        raise SystemExit("kicad-cli not found")
    destination = ROOT / "release/reports/ignored-drc"
    destination.mkdir(parents=True, exist_ok=True)
    summary = ["# Ignored DRC audit", "",
               "Every rule configured as `ignore` in the released KiCad projects was",
               "temporarily changed to `warning`; the released project settings were not modified.", ""]
    total = Counter()
    with tempfile.TemporaryDirectory(prefix="symm60he-full-drc-") as tmp_name:
        tmp = Path(tmp_name)
        for name in BOARDS:
            board_src = ROOT / "pcb" / f"{name}.kicad_pcb"
            pro_src = ROOT / "pcb" / f"{name}.kicad_pro"
            board = tmp / board_src.name
            project = tmp / pro_src.name
            shutil.copy2(board_src, board)
            data = json.loads(pro_src.read_text())
            severities = data["board"]["design_settings"]["rule_severities"]
            enabled = sorted(key for key, value in severities.items() if value == "ignore")
            for key in enabled:
                severities[key] = "warning"
            project.write_text(json.dumps(data, indent=2) + "\n")
            report = destination / f"{name}-all-ignored-enabled.rpt"
            subprocess.run([cli, "pcb", "drc", "--refill-zones", "--all-track-errors",
                            "--severity-all", "-o", str(report), str(board)],
                           cwd=tmp, check=False, capture_output=True, text=True)
            all_counts = Counter(re.findall(r"^\[([^]]+)\]", report.read_text(), re.M))
            # The full run also emits rules that were already warnings in the
            # normal project. This audit reports only rules newly re-enabled.
            counts = Counter({rule: all_counts[rule] for rule in enabled
                              if all_counts[rule]})
            total.update(counts)
            summary += [f"## {name}", "", f"Re-enabled rules: {', '.join(enabled)}", ""]
            if counts:
                summary += ["| Rule | Findings |", "|---|---:|"]
                summary += [f"| `{rule}` | {count} |" for rule, count in sorted(counts.items())]
            else:
                summary.append("No findings under the re-enabled rules.")
            summary.append("")
    summary += ["## Interpretation", ""]
    if not total:
        summary.append("No ignored-rule findings were produced on any board.")
    else:
        summary += ["The raw reports above are the authority for each location. Only findings",
                    "from rules that were ignored in the released projects are counted here.",
                    "The courtyard and footprint-type findings are metadata or documentation",
                    "issues. Silkscreen conflicts are clipped to solder-mask openings by",
                    "`tools/releases/release.py`. Physical copper, drill and routed-slot rules are enabled",
                    "in the released projects and are therefore not part of this ignored-rule",
                    "inventory. The raw reports remain the authority for every location.", "",
                    "| Rule | Total |", "|---|---:|"]
        summary += [f"| `{rule}` | {count} |" for rule, count in sorted(total.items())]
    out = ROOT / "release/reports/ignored-drc-audit.md"
    out.write_text("\n".join(summary) + "\n")
    print(out)
    print(dict(sorted(total.items())))


if __name__ == "__main__":
    main()
