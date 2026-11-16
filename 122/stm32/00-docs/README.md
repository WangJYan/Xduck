# 122 STM32

STM32 从 2026-11-11 IMU 旋转适配烧录记录的 Git 基线和 `source.patch` 恢复；构建时必须使用 `H7DM_IMU_MOUNT_Z180=ON`、`H7DM_CAN_CAPTURE=ON`、`H7DM_BENCH_ID1_ONLY=OFF`。完整参数见 `stm32/BUILD-INFO.txt`。未发现该固件的完整历史源码哈希清单，因此不宣称构建可逐字节复现。

工程入口：`../10-source/stm32-h7-dm/CtrBoard-H7_ALL/CMakeLists.txt`。源码哈希：`SOURCE-SHA256SUMS`；来源：`PROVENANCE.json`。本次未编译、烧录或操作电机。
