# xduck

**连接机器人模型、仿真训练、策略部署与真机控制的项目仓库。**

xduck 围绕 Xduck 与 Rider 系列机器人，整理从模型迭代到真机运行的工程资源：机器人定义与网格、仿真训练任务、ONNX 策略及配套 Python 消费代码，以及 RK3566 上位机与 STM32 H7 下位机程序。

`main` 只保存整个仓库的介绍与导航。具体源码、模型和实验资料按用途放在对应分支中。

## 分支导航

| 分支 | 主要内容 | 从这里开始 |
| --- | --- | --- |
| **[model](https://github.com/x-rangecraft/Xduck/tree/model)** | 机器人模型与版本迭代，包括机器人定义、几何网格和配套配置 | [模型版本介绍](https://github.com/x-rangecraft/Xduck/blob/model/README.md) |
| **[simulation](https://github.com/x-rangecraft/Xduck/tree/simulation)** | 按机器人版本组织的仿真与训练工程、任务配置、策略和评估资料 | [仿真与训练介绍](https://github.com/x-rangecraft/Xduck/blob/simulation/README.md) |
| **[simtoreal](https://github.com/x-rangecraft/Xduck/tree/simtoreal)** | 电机仿真模型、策略部署版本、ONNX 与配套 Python 接口文件 | [Sim-to-Real 介绍](https://github.com/x-rangecraft/Xduck/blob/simtoreal/README.md) |
| **[driver](https://github.com/x-rangecraft/Xduck/tree/driver)** | 四台设备的 RK3566、STM32 完整控制工程、协议与设备适配说明 | [设备驱动与控制介绍](https://github.com/x-rangecraft/Xduck/blob/driver/README.md) |

## 项目组成

### 机器人模型 · model

保存 `DUCK_V1.0.2` 至 `DUCK_V2.0.2` 的模型资源与历史迭代。各版本包含对应的机器人定义、网格与配置，记录执行器、质量、关节限位、零位和传感器坐标等变化。

[查看模型分支](https://github.com/x-rangecraft/Xduck/tree/model)

### 仿真与训练 · simulation

按机器人版本与任务保存训练工程。`v1/` 对应第一版 xduck1，包含行走、站立、坐站和倒地恢复等任务；`v2/` 对应第二版 xduck2，包含行走及坐下／起立相关训练资料。

训练配置、模型、检查点、导出策略、评估视频和验证范围以各任务说明为准。

[查看仿真与训练分支](https://github.com/x-rangecraft/Xduck/tree/simulation)

### 策略部署 · simtoreal

整理 GF43X40 电机仿真模型、UniLab 迁移包，以及 xduck1、xduck2 的历史策略部署版本。ONNX 模型和配套 Python 策略代码按对应版本保存，便于检查输入输出契约并追溯部署资源。

[查看 Sim-to-Real 分支](https://github.com/x-rangecraft/Xduck/tree/simtoreal)

### 设备驱动与控制 · driver

设备控制采用 RK3566 与 STM32 H7 分工：RK3566 运行 Linux 服务，负责策略推理、控制调度、网页和通信；STM32 负责电机总线、底层反馈与实时保护。两端通过 USB 串口上的 DMUSB v4 协议协作。

| 设备目录 | 名称 | 配置概要 |
| --- | --- | --- |
| [121](https://github.com/x-rangecraft/Xduck/tree/driver/121) | **xduck1** | 14 电机 GF/I2RT 配置的基础设备版本 |
| [122](https://github.com/x-rangecraft/Xduck/tree/driver/122) | **xduck2** | 14 电机配置，包含专用 IMU 适配、蓝牙屏和策略调度相关改动 |
| [124](https://github.com/x-rangecraft/Xduck/tree/driver/124) | **Rider** | DM-J10422P-2EC 十电机版本，采用 5+5 关节布局 |
| [125](https://github.com/x-rangecraft/Xduck/tree/driver/125) | **Rider Mini** | 十二电机版本，使用独立 Yesense USB IMU |

每台设备保留 `rk3566/`、`stm32/` 两个工程入口，内部统一使用以下分区：

```text
00-docs/       工程说明、协议、来源与校验记录
10-source/     完整源码工程
20-build/      构建缓存
30-artifacts/  交付产物
40-deploy/     部署说明
50-logs/       构建、测试与部署日志
60-tools/      工程工具
90-temp/       临时文件
```

RK3566 的源码目录统一命名为 `10-source/xduck/`；STM32 固件位于 `10-source/stm32-h7-dm/`。

[查看完整设备代码](https://github.com/x-rangecraft/Xduck/tree/driver)

## 获取与使用

根据用途选择分支，例如获取设备控制代码：

```sh
git clone --branch driver https://github.com/x-rangecraft/Xduck.git
cd Xduck
```

获取其他内容时，将 `driver` 替换为 `model`、`simulation` 或 `simtoreal`。具体环境、构建参数和操作步骤见对应分支的 README。

各分支按用途独立维护。使用模型或策略接入设备时，应结合对应版本核对关节名称与顺序、方向、零位、限位、观测定义和电机参数；模型版本号与设备编号之间的适配关系以具体工程记录为准。

## 来源与维护

源码来源、模型变更、构建参数和已有验证记录保存在各分支内。历史资料用于追溯，仿真评估、源码校验和发布健康检查各自代表不同的验证范围，实机状态以对应设备的验收记录为准。

第三方代码与资源遵循各自的许可证和版权声明，具体内容见对应目录。
