#!/usr/bin/env python3
"""Verify that installed exact STEP artifacts match the recorded source hash."""
from pathlib import Path
import hashlib
import json


ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = ROOT / "case/fusion360/models"
MANIFEST = MODEL_DIR / "model-provenance.json"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    data = json.loads(MANIFEST.read_text())
    exact = 0
    pending = []
    unresolved = []
    for item in data["models"]:
        status = item["status"]
        relative = item.get("file")
        if "not installed" in status:
            pending.append(item["mpn"])
        elif "installed" in status:
            path = MODEL_DIR / relative
            if not path.is_file():
                raise RuntimeError(f"missing installed model: {relative}")
            actual = sha256(path)
            if actual != item.get("sha256"):
                raise RuntimeError(
                    f"hash mismatch for {relative}: {actual}")
            if not path.read_bytes()[:32].startswith(b"ISO-10303-21"):
                raise RuntimeError(f"not a STEP exchange file: {relative}")
            exact += 1
        elif "not selected" in status:
            unresolved.append(item["assembly_item"])
    print(f"model provenance: PASS; {exact} exact source-locked STEP files")
    print("pending authenticated vendor downloads: " + ", ".join(pending))
    print("exact product not selected: " + ", ".join(unresolved))


if __name__ == "__main__":
    main()
