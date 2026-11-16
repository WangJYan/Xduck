"""Compile the production topology tables, without opening hardware."""
from pathlib import Path
import subprocess, tempfile
source = (Path(__file__).resolve().parents[1] / "App/Src/motor_app.cpp").read_text()
start = source.index("typedef struct {")
end = source.index("static const unsigned char kMotorAppCanPort1MitList[]")
tables = source[start:end]
prefix = """
#include <cassert>
#include "motor_profile.h"
#define H7DM_RIDER_5X5 1
#define H7DM_BENCH_ID1_ONLY 0
#define MOTOR_APP_POSITION_RAD 3.0f
#define MOTOR_APP_WORKING_TORQUE_NM 23.5f
"""
main = """
int main() {
  static_assert(sizeof(kMotorAppDefaultConfig)/sizeof(kMotorAppDefaultConfig[0]) == 14);
  for (unsigned i=0; i<14; ++i) {
    const auto &c = kMotorAppDefaultConfig[i];
    assert(c.port == (i<5 ? 1 : i<10 ? 2 : 0));
    assert(c.can_id == (i<10 ? i+1 : 0));
  }
}
"""
with tempfile.TemporaryDirectory() as folder:
    path = Path(folder)
    (path / "test.cpp").write_text(prefix + tables + main)
    subprocess.run(["c++", "-std=c++17", "-I", str(Path(__file__).resolve().parents[1]/"App/Inc"), str(path / "test.cpp"), "-o", str(path / "test")], check=True)
    subprocess.run([str(path / "test")], check=True)
print("PASS: CAN1 1-5, CAN2 6-10, four empty DMUSB slots")
