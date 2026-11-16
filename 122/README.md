# 122 设备源码

设备：`rk3566-2`；SoC：`4c6538ccf4b6191d`；STM32 USB 序列号：`354C35743333`。

- `rk3566/microduck/`：从该设备只读取得的完整 Rust workspace。
- `stm32/stm32-h7-dm/`：对应 STM32 工程。

STM32 从 2026-11-11 IMU 旋转适配烧录记录的 Git 基线和 `source.patch` 恢复；构建时必须使用 `H7DM_IMU_MOUNT_Z180=ON`、`H7DM_CAN_CAPTURE=ON`、`H7DM_BENCH_ID1_ONLY=OFF`。完整参数见 `stm32/BUILD-INFO.txt`。未发现该固件的完整历史源码哈希清单，因此不宣称构建可逐字节复现。

RK3566 当前安装版本、下载校验及与发布源码清单的对照见 `rk3566/PROVENANCE.json`；STM32 来源见 `stm32/PROVENANCE.json`。原源码说明中的 `10-source/`、`20-build/` 路径沿用原开发环境，本目录按设备归档。
