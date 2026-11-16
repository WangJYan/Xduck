from pathlib import Path
import subprocess,json,time,os
B=Path(__file__).resolve().parents[1];uv='/home/xingchen/.local/bin/uv';python='/home/xingchen/Xduck/stable_step_side400_20261105/project/.venv/bin/python';assert (B/'audit/SMOKE_COMPLETE.json').exists();smoke=json.loads((B/'audit/SMOKE_COMPLETE.json').read_text());assert smoke['new_updates']==2
command=[uv,'run','--no-project','--python',python,str(B/'tools/train_continuation.py')]
with (B/'logs/train.log').open('w') as log:
 p=subprocess.Popen(command,cwd=B,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL);(B/'TRAIN_LAUNCH.json').write_text(json.dumps(dict(pipeline_pid=os.getpid(),launcher_pid=p.pid,command=command,parent_stage='P12',P13_excluded=True,total_updates=100,started_unix=time.time()),indent=2));code=p.wait()
if code!=0:raise SystemExit(code)
with (B/'logs/export.log').open('w') as log:subprocess.run([uv,'run','--no-project','--python',python,str(B/'tools/export_final.py')],cwd=B,stdout=log,stderr=subprocess.STDOUT,check=True)
