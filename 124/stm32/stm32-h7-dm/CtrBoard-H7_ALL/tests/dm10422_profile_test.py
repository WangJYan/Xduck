"""Production DM profile/readback gate regression. No device or motor access."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
source=(root/'App/Src/motor_app.cpp').read_text()
a=source.index('static unsigned char MotorApp_VerifyDmProfile(')
b=source.index('\n}\n#endif',a)+2
body=source[a:b]
pre=r'''
#define H7DM_DM_J10422P 1
#include "motor_profile.h"
#include <cassert>
#include <cstring>
#include <map>
#include <limits>
static unsigned bits(float f){unsigned v;memcpy(&v,&f,4);return v;}
struct Motor_t {
 std::map<unsigned char,unsigned> registers;
 unsigned reads=0, adopted=0;
 float p=0,v=0,t=0;
 Motor_t():registers{{0x08,4},{0x07,20},{0x0a,1},{0x23,8},{0x15,bits(12.5663706f)},
 {0x16,bits(20.0f)},{0x17,bits(500.0f)},{0x09,8000}}{}
 unsigned GetCANID(){return 4;} unsigned GetMasterID(){return 20;}
 unsigned char ReadRegister(unsigned char r,unsigned *out){reads++;auto i=registers.find(r);if(i==registers.end())return 0;*out=i->second;return 1;}
 void SetMITFullRange(float lo,float hi,float vlo,float vhi,float tlo,float thi,float kp0,float kp1,float kd0,float kd1){
   assert(lo==-hi && vlo==-vhi && tlo==-thi && kp0==0 && kp1==500 && kd0==0 && kd1==5);
   p=hi;v=vhi;t=thi;adopted++;
 }
 // Deliberately no WriteRegister/SaveParameters/enable member: readback gate cannot use them.
};
'''
post=r'''
int main(){
 static_assert(120000000/(2*(1+MOTOR_PROFILE_DATA_SEG1+MOTOR_PROFILE_DATA_SEG2))==4000000,"FD rate");
 assert(MOTOR_PROFILE_WORKING_TMAX == 400.0f);
 assert(MOTOR_PROFILE_WORKING_VMAX > 12.5663f && MOTOR_PROFILE_WORKING_VMAX < 12.5664f);
 Motor_t ok; assert(MotorApp_VerifyDmProfile(&ok)); assert(ok.reads==8 && ok.adopted==1);
 assert(ok.p==12.5663706f && ok.v==20.0f && ok.t==500.0f);
 for(auto change:std::map<unsigned char,unsigned>{{0x08,5},{0x07,0},{0x0a,2},{0x23,9},
      {0x15,bits(12.5f)},{0x16,bits(10.0f)},{0x17,bits(28.0f)},{0x09,0}}){
  Motor_t m;m.registers[change.first]=change.second;assert(!MotorApp_VerifyDmProfile(&m));assert(!m.adopted);
 }
 for(float value:{std::numeric_limits<float>::quiet_NaN(),std::numeric_limits<float>::infinity(),-1.0f}){
  Motor_t m;m.registers[0x17]=bits(value);assert(!MotorApp_VerifyDmProfile(&m));assert(!m.adopted);
 }
 Motor_t slow;slow.registers[0x09]=8001;assert(!MotorApp_VerifyDmProfile(&slow));
 Motor_t missing;missing.registers.erase(0x15);assert(!MotorApp_VerifyDmProfile(&missing));
 assert(!MotorProfile_IsFaultState(0) && !MotorProfile_IsFaultState(1));
 for(unsigned char state=2;state<16;state++)assert(MotorProfile_IsFaultState(state));
}
'''
with tempfile.TemporaryDirectory() as folder:
 path=Path(folder)/'test.cpp';path.write_text(pre+body+post)
 subprocess.run(['c++','-std=c++17','-Wall','-Wextra','-Werror','-I',str(root/'App/Inc'),str(path),'-o',str(path.with_suffix(''))],check=True)
 subprocess.run([str(path.with_suffix(''))],check=True)
print('PASS: 4M FD, exact readback scaling, no writes, invalid profiles rejected, DM encoder faults')
