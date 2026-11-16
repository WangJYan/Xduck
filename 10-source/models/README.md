# Xduck 模型资源

本目录保留独立的模型版本和头部设计。

## DuckResource 版本模型

以下 14 个完整版本从 [DuckResource 的 Model 目录](https://github.com/x-rangecraft/DuckResource/tree/6d1e7e48dd83f3e54c19116abc6adf251a52efee/Model) 原样复制，来源提交为 `6d1e7e48dd83f3e54c19116abc6adf251a52efee`。每版包含来源仓库中该版本的全部文件，保留原有相对路径、文件名及内容。

- [DUCK_V1.0.2/](DUCK_V1.0.2/)
- [DUCK_V1.0.3/](DUCK_V1.0.3/)
- [DUCK_V1.0.4/](DUCK_V1.0.4/)
- [DUCK_V1.0.5/](DUCK_V1.0.5/)
- [DUCK_V1.0.6/](DUCK_V1.0.6/)
- [DUCK_V1.0.7/](DUCK_V1.0.7/)
- [DUCK_V1.1.0/](DUCK_V1.1.0/)
- [DUCK_V1.1.1/](DUCK_V1.1.1/)
- [DUCK_V1.1.2/](DUCK_V1.1.2/)
- [DUCK_V1.1.3/](DUCK_V1.1.3/)
- [DUCK_V1.1.4/](DUCK_V1.1.4/)
- [DUCK_V1.1.5/](DUCK_V1.1.5/)
- [DUCK_V2.0.1/](DUCK_V2.0.1/)
- [DUCK_V2.0.2/](DUCK_V2.0.2/)

每版的文件布局以其目录内容为准：MuJoCo 模型通常从 `scene.xml` 加载；有 Isaac Lab 资产的版本需保留完整 `isaaclab/` 目录。不要跨版本混用网格、配置和机器人定义。

本次范围为 V1.0.2 至 V2.0.2 的正式三段版本目录，不含历史命名 `DUCK_V1.01`、外层 ZIP 副本及共享 `Validation/` 目录。各版本内部的文档和验证资料均随版本保留。

[IMPORT-MANIFEST.json](IMPORT-MANIFEST.json) 记录来源、版本范围及全部 885 个文件的 Git blob SHA-1，可与来源提交逐项比较。本次验证文件复制完整性，未重新执行仿真或真机测试。

## 头部设计

[head_v1/](head_v1/) 为此分支原有的头部设计与装配资源。
