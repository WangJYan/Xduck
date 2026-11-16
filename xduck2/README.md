# Xduck 2｜Sim-to-Real 策略迭代

本目录按桌面提供的文件保存 Xduck 2 的 **v1、v2** 策略。v1 包含行走、站立恢复和坐下／起立相关文件；v2 保存一个 P12 flexDR100 模型候选。

## 版本记录

### [v1](v1/)：行走、站立与坐起

| 文件 | 作用 |
| --- | --- |
| `xc_walk.onnx` | 行走模型。 |
| `xc_standing.onnx` | 站立／恢复模型。 |
| `xc_walk_stand.py` | 行走与站立共用的 API-v2 策略接口；脚本标注适用于 v2.0.2 P12 Walk 与 Stand／recovery。 |
| `xc_site.onnx` | 坐下／起立相关模型。 |
| `xc_site.py` | 坐下／起立接口；脚本标注使用当前关节速度反馈，并在模式切换时保留状态。 |

### [v2](v2/)：P12 flexDR100 候选

目录包含 `P12_flexDR100.onnx`。文件名标识其为 P12 的 flexDR100 变体；本次归档没有配套接口、训练配置或评估记录，因此无法确认它与 v1 的训练继承关系或效果差异。

## 模型与接口配对

`v1/xc_site.py` 内嵌配置记录的模型为 `xduck_v202_descent600.onnx`，记录的 SHA-256 为：

```text
54f2feee7aac0e527f7bc23146e56c074aada6de8d331acdb3e7b04c8c41cf2b
```

归档的 `v1/xc_site.onnx` 的 SHA-256 为：

```text
b74e00f47832e4c14e26ccc3b4f6f6ac23b490977c44554f6caf4fe5eac1e9b2
```

两者不一致，请先确认模型和脚本的实际配对。v2 也需要先找到对应的部署接口和配置，再核对观测与动作维度、关节顺序、IMU 坐标及控制周期。Python 策略接口由部署框架调用，不能单独替代机器人驱动。
