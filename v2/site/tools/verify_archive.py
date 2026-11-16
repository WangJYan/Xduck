"""Verify tracked site archive bytes without importing robot or ML runtimes."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'PACKAGE_MANIFEST.json').read_text())
for row in manifest['files']:
 p=root/row['path']
 if not p.is_file():raise SystemExit('Missing: '+row['path'])
 if p.stat().st_size!=row['bytes']:raise SystemExit('Size mismatch: '+row['path'])
 if hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:raise SystemExit('SHA256 mismatch: '+row['path'])
onnx=hashlib.sha256((root/'policy/xc_site.onnx').read_bytes()).hexdigest()
assert onnx==manifest['model_sha256']
print(f"Verified {len(manifest['files'])} files; support400 ONNX {onnx}")
