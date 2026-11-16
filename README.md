# Xduck Sim-to-Real

本分支整理电机仿真模型与 Xduck 策略的实机部署版本。版本文件按桌面提供的目录归档；各版本之间的说明依据文件名和随包脚本，不能单独证明训练继承关系或实机效果。

| 目录 | 内容 |
| --- | --- |
| [motor](motor/README.md) | GF43X40 电机模型与 UniLab 迁移包 |
| [xduck1](xduck1/README.md) | 第一组策略版本 v4–v11 |
| [xduck2](xduck2/README.md) | 第二组策略版本 v1–v2 |

根目录中 `xc_upload_*` 和 `xduck_calibrated_sitstand_20260930_model_63` 是分支原有的历史上传包，保留供参考。各版本中的 ONNX 与 Python 策略接口应按对应训练配置和部署框架核对后使用。
