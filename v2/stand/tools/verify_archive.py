"""Verify archive identity without importing training code or activating hardware."""
from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / "PACKAGE_MANIFEST.json").read_text())
errors = []
for relative, expected in manifest["files"].items():
    path = root / relative
    if not path.is_file():
        errors.append(f"missing: {relative}")
        continue
    data = path.read_bytes()
    if len(data) != expected["bytes"]:
        errors.append(f"size mismatch: {relative}")
    if hashlib.sha256(data).hexdigest() != expected["sha256"]:
        errors.append(f"sha256 mismatch: {relative}")
if errors:
    raise SystemExit("\n".join(errors))
print(f"PASS: {len(manifest['files'])} files verified")
