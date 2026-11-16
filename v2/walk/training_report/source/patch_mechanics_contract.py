from pathlib import Path
B=Path('/home/xingchen/Xduck_branches/xduck_2_0_2_P12_flexDR100_20261114')
for name in ['rigid_startcourse.py','balanced_env.py']:
 p=B/'workspace/turn_start_heading400_20261105/project/src/unilab/envs/locomotion/xduck_gf43x40'/name
 lines=p.read_text().splitlines();out=[];changed=0
 for line in lines:
  if line.strip().startswith('assert len(self._passive_qpos_indices)') and ('==0' in line or '== 0' in line):
   indent=line[:len(line)-len(line.lstrip())];out.extend([indent+'if cfg.flexible_dr_enabled:',indent+'    assert len(self._passive_qpos_indices)==48 and cfg.physics_microsteps==16',indent+'else:',indent+'    assert len(self._passive_qpos_indices)==0 and cfg.physics_microsteps==1']);changed+=1
  else:out.append(line)
 assert changed==1,(name,changed);p.write_text('\n'.join(out)+'\n');print('Extended private mechanics contract',name)
