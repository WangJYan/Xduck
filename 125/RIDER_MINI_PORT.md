# Rider Mini 适配记录

状态：RK3566 服务与 STM32 固件已部署到 125 板；控制链路和网页已验证，电机供电与 CAN 接通后的反馈及运动验收待完成。

## 已确认的电机契约

电机与原工程同型号，I2RT/CAN FD 通信协议和速率不变。12 个电机按物理 ID 1–12 排列：CAN1 承载奇数 ID（右侧），CAN2 承载偶数 ID（左侧）。以下均为 rad；逻辑零位全部为 0。限位来自 186 当前部署的 `robot_driver` MIT **软件**限位，并非机械硬限位。

| ID | CAN | 关节 | MIT 软件限位 rad | 站立 rad |
| --- | --- | --- | --- | --- |
| 1 | CAN1 | `right_hip_pitch` | [-1.80, 2.00] | 0.308279 |
| 2 | CAN2 | `left_hip_pitch` | [-2.00, 1.80] | -0.308279 |
| 3 | CAN1 | `right_hip_roll` | [-0.50, 0.50] | 0 |
| 4 | CAN2 | `left_hip_roll` | [-0.50, 0.50] | 0 |
| 5 | CAN1 | `right_hip_yaw` | [-3.80, 3.30] | 0 |
| 6 | CAN2 | `left_hip_yaw` | [-3.30, 3.80] | 0 |
| 7 | CAN1 | `right_knee_pitch` | [-1.10, 0.75] | 0.300000 |
| 8 | CAN2 | `left_knee_pitch` | [-0.75, 1.10] | -0.300000 |
| 9 | CAN1 | `right_shank_pitch` | [-0.80, 1.10] | 0.207704 |
| 10 | CAN2 | `left_shank_pitch` | [-1.10, 0.80] | -0.207704 |
| 11 | CAN1 | `right_foot_pitch` | [-1.00, 1.43] | 0.152691 |
| 12 | CAN2 | `left_foot_pitch` | [-1.43, 1.00] | -0.152691 |

这张表优先于最初口述的左右侧归属：后续提供的逐电机编号表指定奇数为右侧、偶数为左侧。

## 已实施

- STM32 默认路由改为 CAN1/CAN2 各六电机，FDCAN 接收/发送和事件 FIFO 容量按 6+6 配置；原 FD+BRS 时序、I2RT 编码与电机型号保持不变。STM32 默认位置限制使用上表数值。
- RK3566 侧的状态帧、目标帧、IPC 关节列表、标定默认值、站姿和网页电机表改为 12 关节 ID 顺序。网页与服务端模型上传要求提供匹配的 `policy.py`。
- 出厂 `robotd.toml` 禁用策略与动作槽位、音频、ToF 乐器、视觉检测、合唱和摄像头。网页服务以 HTTP-only 模式运行，保留网页控制与模型管理。Rider Mini 发布清单不再打包声音、ToF、视觉检测二进制及动作模型；旧走/站 ONNX 暂仅作为禁用策略时的槽位占位文件。
- Rider Mini 尚无 Walk/Stand 模型及 `policy.py`。内置默认行走策略为拒绝运行的占位实现，策略出厂禁用。
- 对外显示名统一为 `Rider Mini`：网页、Android BLE App、configd 出厂默认值已更新；125 板卡的持久名称文件和蓝牙 Alias 已设置为 `Rider Mini`。Linux 登录账号保持 `xduck4`。

## 待完成和部署门槛

- 提供新的 Walk/Stand 模型及其输入/输出契约和 `policy.py`，在 12 关节台架验证后才能启用策略。旧 14 输出模型不可使用。
- 125 板卡已只读核对：`192.168.50.125:888`、hostname `rk3566-4`、SoC serial `e104cc5db286be72`、Debian 12、KICKPI K11C；STM32 串口为 `/dev/serial/by-id/usb-STMicroelectronics_STM32_Virtual_ComPort_315C365A3233-if00`。登录账号保持 `xduck4`，对外显示名为 `Rider Mini`。
- 在电机主电源及 CAN1/CAN2 接通后，验证 12 路反馈、软限位、失能、初始化和姿态。目前 12 路反馈均未更新，电机控制未使能。
- 旧媒体/动作源码及依赖仍在代码包内，运行时已禁用，尚需继续清理发布内容与无效接口。

## 2026-09-28 部署记录

- RK3566 板端使用 Rust 1.89 编译通过，发布包版本为 `0.10.0-dev.local.1790582910.g02f38e4`；签名 dry run 与首次安装成功。`robotd`、`updaterd`、`configd`、`btd`、`padd`、`mediad`、`xpad-usbd` 均 active，`tofd` 停止。
- Mac 上的 Horco CMSIS-DAP（序列号 `600c3ea8`）通过 SWD 确认 STM32H723 设备 ID `0x483`。烧录 `20-build/stm32/stm32-h7-dm/rider-mini-release/CtrBoard-H7_ALL.elf` 后，OpenOCD 读回校验 `Verified OK` 并复位。
- 烧录前固件前 128 KiB 的备份位于 `30-artifacts/stm32/stm32-h7-dm/rider-mini-preflash-2026-09-28/stm32h723-original-first-128k.bin`；原固件非空数据到约 83 KiB。整片备份在 344 KiB 处因探针停止响应而中断，故不应把较大的部分文件当作完整镜像。
- `robotctl health` 显示 50 Hz 控制循环、STM32 bus ok、IMU ready；启动日志显示 `joints=12`、`driving=false`、策略禁用。网页 `http://192.168.50.125:8080/` 返回 HTTP 200，`robot.models` 列表接口可用且暂无模型。
- 电机尚未上电或 CAN 未接好，STM32 报 `can_tx_drop` / `timeout_config_failed`，12 路反馈均过期。用户确认当前硬件连接未完成；因此健康状态仅证明 RK3566 与 STM32 的 USB/IMU 链路，不代表电机总线验收通过。

## 2026-09-30 Yesense USB IMU 移植

186 当前连接的 IMU 为 Yesense YIS 协议设备，USB VID:PID `1a86:55d4`，使用 `cdc_acm`；稳定路径为 `/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B31017780-if00`，串口 460800 8N1。186 上只读采样 3.0045 秒收到 600 个 67 字节有效帧，约 199.70 Hz，校验和解析错误为 0；数据包含加速度、角速度、欧拉角和四元数。

`duck-control/src/yesense.rs` 独立读取 USB 流，保留最新样本，不形成控制队列；四元数按 wxyz 归一化，角速度由 deg/s 转 rad/s，加速度保留 m/s² 比力，重力为 body→world 四元数的逆旋转。安装轴向暂沿用 186 的 FLU/ENU、零安装补偿配置，接入 125 后需做实物轴向验证。

`DynamixelIo` 保留 STM32 DMUSB v4 电机及电池通信，并在每个 50 Hz 状态读取时合并 USB IMU。上层姿态、策略、里程计、跌倒检测和 IMU 就绪/过期门禁使用新数据；策略增加 `imu.acceleration`，实验记录增加 `imu_acceleration`。STM32 的帧布局、固件、能力位、故障位和自身保护不变。USB IMU 缺失、断连或超过 100 ms 未更新时拒绝上层样本及使能，不回退 BMI088；STM32 失能命令和正常状态接收继续可用，重新连接后须重新显式使能。

默认 `bus.imu_port` 已改为上述稳定 USB 路径，旧预留 `/dev/ttyS2` 在加载配置时迁移到 USB 路径，STM32 已配置的 `bus.port` 保持原值。

按用户要求，当前已完成源码上传、无硬件自动化测试和板端 release 编译；IMU 尚未接到 125，运行服务尚未切换。待接线后安装已构建版本，检查枚举、200 Hz 数据、静止/轴向、拔插及上层状态来源，不进行电机运动测试。

验证：`duck-control` 62 项、参数相关 25 项、策略运行器 1 项、策略实验 7 项通过。参数全套测试中另有两项此前 Rider Mini 迁移留下的默认配置断言不一致（摄像头默认关闭、STM32 315C/3859 序列号差异），未改变这些硬件默认值；对应失败与过滤后结果均已留证。新增虚拟串口/协议测试覆盖实采帧、分片、坏校验、缺字段、零四元数、单位转换、序列号回绕、过期、断连、快速重插锁存和 IMU 缺失时仍可完成 STM32 失能命令。

板端 release 产物归档为 `/home/xduck4/xrange/30-artifacts/rk3566/microduck/native-release-20260930-040608/`，固定构建流程已完成 ARM aarch64 ELF 校验，含 `SHA256SUMS` 与 `BUILD-INFO.txt`。本地证据位于 `50-logs/test/imu/yesense-usb-20260930/`，`summary.json` 记录源文件 SHA256、测试结果和待实物验收状态。运行服务尚未安装此版本，STM32 固件未改。

## 2026-10-15 USB IMU 切换生效

用户确认切换后，按固定部署流程重新构建、签名并通过 updater 健康门禁，结果 `applied`。运行版本从 `0.10.0-dev.local.1790587555.g02f38e4` 切换到 `0.10.0-dev.local.1792036035.g02f38e4`。`/etc/robot/robotd.toml` 的 `bus.imu_port` 已明确指向 Yesense 稳定 USB 路径，STM32 的 `bus.port` 保持原样；原配置备份在板端 `50-logs/deploy/rk3566/microduck/usb-imu-switch-20261015-114709/`。

切换前 USB IMU 实采 5.001 秒、1000 个有效 67 字节帧，约 199.94 Hz，校验错误 0。切换后新 robotd 同时打开 `/dev/ttyACM0`（STM32）与 `/dev/ttyACM1`（Yesense），日志确认两者就绪；上层 IMU 姿态已来自 Yesense。30.35 秒观察得到 31 个状态样本，控制速率 49.999 Hz、期间新增 missed 为 0、bus 连续错误 0、IMU ready 且连续过期为 0。12 电机全程 flags=3（在线且失能），control_state=relaxed；没有进行电机运动、物理拔插或安装轴向动作测试。robotd/configd/updaterd/btd/padd/mediad/xpad-usbd 均 active。系统原有 console-setup、rkaiq_3A、systemd-fsck-prepare 三项失败 unit 未变化。

板端产物为 `30-artifacts/rk3566/microduck/native-release-20261015-034715/`；本地实测证据在 `50-logs/test/imu/usb-imu-switch-20261015/`，部署及进程验证证据在 `50-logs/deploy/rk3566/microduck/usb-imu-switch-20261015-114709/`。本节更新了前述 9 月 30 日“仅编译、未安装”的历史状态，当前已经启用 USB IMU。
