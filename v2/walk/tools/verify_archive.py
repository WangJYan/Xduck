"""Verify committed archive bytes and selected checkpoint/physics identities. Read-only."""
from pathlib import Path
import gzip,hashlib,json,tarfile
B=Path(__file__).resolve().parents[1]
def digest(f):
 h=hashlib.sha256()
 for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def check():
 m=json.loads((B/'PACKAGE_MANIFEST.json').read_text())
 for name,info in m['files'].items():
  p=B/name;assert p.stat().st_size==info['bytes'],name
  with p.open('rb') as f:assert digest(f)==info['sha256'],name
 with gzip.open(B/'archives/effective_training.mjb.gz','rb') as f:assert digest(f)==m['physics_sha256']
 selected={'runs/P12/ppo_run/flex_update_100.pt':m['final_checkpoint_sha256'],'inputs/parent_P12_399.pt':m['parent_checkpoint_sha256']}
 with tarfile.open(B/'archives/flex_continuation_runtime.tar.gz','r:gz') as t:
  for name,expected in selected.items():
   with t.extractfile(name) as f:assert digest(f)==expected,name
 evidence=json.loads((B/'training_report/REMOTE_TRAINING_EVIDENCE.json').read_text())
 with tarfile.open(B/'archives/rigid_lineage_checkpoints_and_sources.tar.gz','r:gz') as t:
  for s in evidence['stages']:
   name='checkpoints/'+s['stage']+'.pt'
   with t.extractfile(name) as f:assert digest(f)==s['complete']['sha256'],name
 print(json.dumps({'status':'PASS','files':len(m['files']),'selected_rigid_checkpoints':len(evidence['stages']),'flex_checkpoint_parent_and_physics':'SHA256 verified','onnx_sha256':m['onnx_sha256']},ensure_ascii=False))
if __name__=='__main__':check()
