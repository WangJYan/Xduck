# xduck1 / stm32 部署入口

本目录用于本设备的发布与部署说明。构建产物归档到 `../30-artifacts/`，过程日志保存到 `../50-logs/deploy/`。

固件工程与 OpenOCD 配置见 [`../10-source/stm32-h7-dm/CtrBoard-H7_ALL/`](../10-source/stm32-h7-dm/CtrBoard-H7_ALL/)。烧录前核对目标设备、STM32 身份及专用构建参数。

历史脚本中的远端路径与下载地址需按实际环境核对，本次没有创建自动部署入口。
