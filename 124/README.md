# 124 设备源码

设备：`rk3566-3`；SoC：`cd291a37700858c3`；STM32 USB 序列号：`385733633134`。

- `rk3566/10-source/xduck/`：从该设备只读取得的完整 Rust workspace。
- `stm32/10-source/stm32-h7-dm/`：对应 STM32 工程。

STM32 来自本地当前工程，与 2026-11-16 DM 峰值版本构建清单 1,093 项全部匹配。该设备为 5+5、DM-J10422P-2EC，构建时必须使用 `H7DM_RIDER_5X5=ON` 和 `H7DM_DM_J10422P=ON`；RK3566 使用 `robotd/rider-5x5` 与 `mediad/rider-5x5` 特性。电机调试验收门禁仍保留，不能只凭源码归档视为已完成运动验收。

RK3566 当前安装版本、下载校验及与发布源码清单的对照见 `rk3566/00-docs/PROVENANCE.json`；STM32 来源见 `stm32/00-docs/PROVENANCE.json`。原源码说明中的 `10-source/`、`20-build/` 路径沿用原开发环境，本目录按设备归档。

## 工程入口

- [RK3566 工程](rk3566/README.md)
- [STM32 工程](stm32/README.md)

两个工程内均使用 `00-docs`、`10-source`、`20-build`、`30-artifacts`、`40-deploy`、`50-logs`、`60-tools`、`90-temp` 分区。
