"""Compile production route setup and CAN scalar codecs against read-back values.
No hardware access. Requires a host C++ compiler.
"""
from pathlib import Path
import subprocess,tempfile,sys
root=Path(__file__).resolve().parents[1]
s=(root/'App/Src/motor_app.cpp').read_text()
h=(root/'Hardware/Src/Motor.cpp').read_text()
constants='\n'.join(line for line in s.splitlines() if line.startswith('#define MOTOR_APP_'))
tables=s[s.index('typedef struct {'):s.index('static const unsigned char kMotorAppCanPort1MitList')]
setup=s[s.index('void MotorApp_ConfigDefault(void)'):s.index('unsigned char MotorApp_ConfigureStartupRegisters(void)')]
codec=h[h.index('static float Motor_LimitFloat('):h.index('static unsigned char Motor_SendSpecialFrame(')]
pre=('#define H7DM_DM_J10422P 1\n#define H7DM_RIDER_5X5 1\n' if '--dm' in sys.argv else '')+'#define H7DM_BENCH_ID1_ONLY '+('1' if '--bench-id1' in sys.argv else '0')+'\n'+r'''
#include <cassert>
#include <cmath>
#include <cstdio>
#include <initializer_list>
#ifndef H7DM_RIDER_5X5
#define H7DM_RIDER_5X5 0
#endif
#define MOTOR_FEEDBACK_ID_P16_OFFSET 16
'''
stubs=r'''
float g_positionMin[24], g_positionMax[24];
unsigned char g_positionLimitsReady;
struct Motor_t {
 unsigned id=0;
 float values[10]{};
 void SetConfig(unsigned char,unsigned short i,unsigned short master){id=i;assert(master==i+16);}
 void SetMITFullRange(float a,float b,float c,float d,float e,float f,float g,float h,float i,float j){float input[10]={a,b,c,d,e,f,g,h,i,j};for(unsigned k=0;k<10;k++)values[k]=input[k];}
} motors[24];
Motor_t* MotorPoint(unsigned char i){return &motors[i];}
void MotorApp_ClearRuntimeState(){}
void MotorApp_PrepareFallbackCommands(){}
'''
post=r'''
int main(){
 MotorApp_ConfigDefault();
 unsigned configured=0;
 for(auto&m:motors) {
  if(!m.id)continue;
  configured++;
  float expected_v=MOTOR_PROFILE_VMAX;
  float expected_t=MOTOR_PROFILE_TMAX;
  assert(m.values[0]==-MOTOR_PROFILE_PMAX&&m.values[1]==MOTOR_PROFILE_PMAX);
  assert(m.values[2]==-expected_v&&m.values[3]==expected_v);
  assert(m.values[4]==-expected_t&&m.values[5]==expected_t);
  #if !H7DM_DM_J10422P
  assert(Motor_FloatToUint(1.0f,m.values[0],m.values[1],16)==35388);
#endif
  float positions[]={-3,-1,0,1,3};
  for(float p:positions){auto raw=Motor_FloatToUint(p,m.values[0],m.values[1],16);assert(std::fabs(Motor_UintToFloat(raw,m.values[0],m.values[1],16)-p)<0.0004f);}
 }
 const unsigned expected = H7DM_BENCH_ID1_ONLY ? 1U : (H7DM_RIDER_5X5 ? 10U : 14U);
 assert(configured==expected);for(unsigned i=1;i<=expected;i++)assert(motors[i].id==i);
 for(unsigned i=expected+1;i<24;i++)assert(motors[i].id==0);
 for(unsigned i=0;i<expected;i++){
  const auto&c=kMotorAppDefaultConfig[i];
  assert(c.can_id==i+1);assert(c.port==(i<5?1:i<10?2:3));
  const auto&w=kMotorAppWireRange[i];
  assert(c.p_min==-3.0f&&c.p_max==3.0f);
  assert(c.v_max<=w.v_max&&c.t_max<=w.t_max);
  #if H7DM_DM_J10422P
  assert(c.t_max==400.0f && w.t_max==500.0f);
  assert(std::fabs(c.v_max-12.5663706f)<0.00001f);
  for(float t:{-400.0f,400.0f}) {
   auto encoded=Motor_FloatToUint(t,-w.t_max,w.t_max,12);
   assert(std::fabs(Motor_UintToFloat(encoded,-w.t_max,w.t_max,12)-t)<0.25f);
  }
#else
  assert(c.t_max==23.5f&&w.t_max==28.0f);
#endif
 }
 printf("motor setup/codecs: %u configured routes, golden encoding, position round trips and capability limits passed\n", expected);
}
'''
with tempfile.TemporaryDirectory() as temp:
 p=Path(temp)/'test.cpp';p.write_text(pre+'#include "'+str(root/'App/Inc/motor_profile.h')+'"\n'+constants+'\n'+tables+stubs+setup+codec+post)
 subprocess.run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-Wno-missing-field-initializers',str(p),'-o',str(p.with_suffix(''))],check=True)
 subprocess.run([str(p.with_suffix(''))],check=True)
