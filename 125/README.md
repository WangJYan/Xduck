# 125 设备源码

设备：`rk3566-4`；SoC：`e104cc5db286be72`；STM32 USB 序列号：`315C365A3233`。

- `rk3566/10-source/xduck/`：从该设备只读取得的完整 Rust workspace。
- `stm32/10-source/stm32-h7-dm/`：对应 STM32 工程。

STM32 来自用户指定的本机 `Rider Mini/DuckResource/Xduck/10-source/stm32/10-source/stm32-h7-dm/` 当前工作区，逐文件复制并保存哈希。[适配记录](rk3566/00-docs/RIDER_MINI_PORT.md) 记录其 2026-09-28 烧录成功，12 个电机按 CAN1 奇数 ID（右侧）、CAN2 偶数 ID（左侧）排列；未找到完整历史源码哈希清单，因此本次归档不宣称与运行固件逐字节可复现对应。

RK3566 当前安装版本、下载校验及与发布源码清单的对照见 `rk3566/00-docs/PROVENANCE.json`；STM32 来源见 `stm32/00-docs/PROVENANCE.json`。原源码说明中的 `10-source/`、`20-build/` 路径沿用原开发环境，本目录按设备归档。

## 工程入口

- [RK3566 工程](rk3566/README.md)
- [STM32 工程](stm32/README.md)

两个工程内均使用 `00-docs`、`10-source`、`20-build`、`30-artifacts`、`40-deploy`、`50-logs`、`60-tools`、`90-temp` 分区。
