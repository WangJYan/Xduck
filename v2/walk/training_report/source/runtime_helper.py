from pathlib import Path
import sys,json,time,os
import numpy as np,torch
from omegaconf import OmegaConf
B=Path(__file__).resolve().parents[1];S=B/'workspace/turn_start_heading400_20261105';PROJECT=S/'project';sys.path[:0]=[str(PROJECT/'src'),str(PROJECT/'scripts'),str(S),str(B/'tools')]
import train_rsl_rl as E
import warp as wp
def atomic(path,data):
 path=Path(path);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(data,indent=2,default=str));os.replace(tmp,path)
def initialize():
 torch.set_num_threads(2);np.random.seed(1105701);torch.manual_seed(1105701);wp.init();wp.set_mempool_release_threshold('cuda:0',0);E.ensure_registries()
def env(c,n,flex=True):
 if flex:from unilab.envs.locomotion.xduck_gf43x40.flex_continue import P12FlexContinueEnv
 e=E.create_env(c,num_envs=n,env_cfg_override=E.build_ppo_env_cfg_override(c))
 if flex:
  from gait_style import install
  install(e,B/'audit/GAIT_STYLE_CONTRACT.json')
 return e
