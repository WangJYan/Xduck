# XDuck simulation：按机体/训练版本归档

本分支分成 `v1/`、`v2/` 两个版本目录。版本目录表示本仓库的归档分组，不等同于桌面策略文件夹名称。

| 目录 | 内容 |
|---|---|
| [v1/](v1/) | 原 simulation 分支全部工程与历史训练任务，包括 walk、stand、xl330、sitstand、walk_narrow_stance 和恢复站；原内容原样迁移，入口见 [原 README](v1/README.md)。 |
| [v2/walk/](v2/walk/) | v2.0.2 机体的行走训练：从零主线至 P12 累计3042次PPO，再加100次柔性/柔性DR续训，最终累计3142次。 |

`v2/walk/policy/P12_flexDR100.onnx` 与桌面 `v3/P12_flexDR100.onnx` 字节一致。P04、P08和P13不在最终选用血缘；800步后退bootstrap与1800步行为克隆不计入PPO轮数。

原 `v1/` 中采用新版 UniLab 的工程和 `v2/` 旧版 Warp 训练归档互相独立。运行和实机适用范围请分别阅读各任务 README。
