# xduck · Rider Mini RK3566

Rider Mini 的 RK3566 上位机程序，设备编号 **125**。Rider Mini 十二电机版本，CAN1 奇数 ID／右侧、CAN2 偶数 ID／左侧。

本工程负责机器人控制调度、策略推理、网页接口、配置管理和设备通信；通过 USB 串口上的 DMUSB v4 协议与配套 STM32 H7 固件协作。

[仓库首页](../../../../README.md) · [配套 STM32](../../../stm32/) · [设计文档](docs/design/) · [操作文档](docs/robot/)

## 本设备配置

上层使用独立 Yesense USB IMU，网页以 HTTP-only 模式运行；策略与模型必须匹配十二关节接口。

设备代码整理于 2026-11-16。具体安装版本和源码来源见 [来源记录](../../00-docs/PROVENANCE.json)，配套固件位于同一设备的 `stm32/` 目录。

## 工程结构

| 目录或文件 | 用途 |
| --- | --- |
| `Cargo.toml` / `Cargo.lock` | Rust workspace 和依赖锁定 |
| `robotd/` | 控制循环、策略管理、标定与安全裁决 |
| `duck-control/` | 电机通信、传感器反馈与硬件适配 |
| `duck-ipc-proto/` / `robotd-params/` | IPC 契约与参数模型 |
| `mediad/` | 网页服务、HTTP 接口和按配置启用的媒体功能 |
| `mediad/webclient/` | 网页界面与实验接口示例 |
| `configd/` | 设备名称、网络和配置管理 |
| `btd/` / `padd/` | 蓝牙与手柄输入适配 |
| `updater/` | 签名更新、健康检查与回滚 |
| `robotctl/` / `duckctl/` | 本机和开发端命令行工具 |
| `deploy/` / `hooks/` / `scripts/` | 配置、打包与安装脚本 |
| `docs/` | 架构、接口与工程说明 |

`robotd` 拥有机器人控制状态并作安全裁决，其他输入入口通过 Unix socket JSON-RPC 转交请求。源码中的模块按设备配置启用，可用功能以本设备的配置和构建特性为准。

## 开发入口

从仓库根目录进入本设备的 workspace：

```sh
cd 125/rk3566/10-source/xduck
```

先查看 [Cargo.toml](Cargo.toml)、[架构说明](docs/design/architecture.md)和[控制服务设计](docs/design/robotd-design.md)。构建前核对目标设备、系统依赖、特性开关及配套 STM32 版本；工程使用 Rust、ONNX 和 Python 策略相关组件。

原工程文档中的 `10-source/`、`20-build/` 等路径描述设备导入前的开发环境。本仓库的工程目录为 `10-source/xduck/`，使用历史安装脚本前需核对目标路径和下载地址。

## 源码校验

从本 workspace 返回 `rk3566/` 工程根目录运行：

```sh
cd ../..
sha256sum -c 00-docs/SOURCE-SHA256SUMS
# macOS：shasum -a 256 -c 00-docs/SOURCE-SHA256SUMS
```

当前清单对应重命名及 README 更新后的仓库文件；`00-docs/DEVICE-SOURCE-SHA256SUMS` 保留导入时设备上的原始路径与哈希，供溯源使用。

## 许可证与来源

本目录使用 xduck 项目名称与介绍。部分代码来源于上游开源工程，保留原有版权、[许可证](LICENSE)与第三方依赖声明。
