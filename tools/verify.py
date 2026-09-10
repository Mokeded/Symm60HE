"""Run every check on the generated boards.  Exits non-zero on any failure.

    python3 verify.py
"""
import subprocess, sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
STEPS = [("structure and containment", "_check_struct.py"),
         ("pad conflicts",             "_check_pads.py"),
         ("nets",                      "netcheck.py"),
         ("routing",                   "routecheck.py")]
bad = 0
for label, script in STEPS:
    if not os.path.exists(script):
        continue
    print("=== %s ===" % label)
    r = subprocess.run([sys.executable, script], capture_output=True, text=True)
    out = (r.stdout + r.stderr).rstrip()
    print(out)
    fail = r.returncode != 0 or any(w in out for w in ("MISMATCH", "OPEN!", "problems", "!!"))
    if "outside outline: 0" in out and out.count("outside outline:") != out.count("outside outline: 0"):
        fail = True
    for line in out.splitlines():
        if "conflicts:" in line and not line.rstrip().endswith(": 0"):
            fail = True
    if fail:
        bad += 1
        print(">>> FAILED\n")
    else:
        print(">>> ok\n")
sys.exit(1 if bad else 0)
