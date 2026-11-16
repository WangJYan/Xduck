#!/bin/sh
set -eu
ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
python3 - "$ROOT" <<'PY_CHECK'
from pathlib import Path
import sys,hashlib
root=Path(sys.argv[1])
expected={'00-docs','10-source','20-build','30-artifacts','40-deploy','50-logs','60-tools','90-temp'}
assert {p.name for p in root.iterdir() if p.is_dir()}==expected,'unexpected or missing project partition'
for part in ('build','test','deploy'):
 assert (root/'50-logs'/part).is_dir(),part
manifest=root/'00-docs/SOURCE-SHA256SUMS'
count=0
for line in manifest.read_text().splitlines():
 digest,name=line.split(None,1)
 p=root/name
 assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==digest,name
 count+=1
sources=[p for p in (root/'10-source').iterdir() if p.is_dir()]
assert len(sources)==1,'expected one intact source project'
project=sources[0]
assert (project/'Cargo.toml').is_file() or (project/'CtrBoard-H7_ALL/CMakeLists.txt').is_file(),'missing build entry'
print(f'layout ok: {root} ({count} source hashes verified)')
PY_CHECK
