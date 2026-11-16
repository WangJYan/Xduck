# XDuck2站立：v2.0.2 v1模型

归档日期：2026-11-16。本目录收录当前桌面 `v1/xc_standing.onnx` 对应的站立模型、训练过程、配置及完成记录。

主训完成 **2700轮**；最终选中权重的修复祖先链另有 **1440轮**，合计250,675,200个控制样本。后续大量更新只训练头部专家，零头部命令使用的冻结身体仍为2700轮版本，不能把它写成身体连续训练4140轮。原计划最后两段16轮pilot没有按原路线完成。

## 文件入口

| 内容 | 位置 |
|---|---|
| 一页概览 | [training_report/一页概览.txt](training_report/一页概览.txt) |
| 完整训练过程 | [training_report/v2.0.2_v1站立模型_训练过程完整说明.txt](training_report/v2.0.2_v1站立模型_训练过程完整说明.txt) |
| 逐阶段轮次、种子、LR、检查点SHA | [training_report/实际阶段与检查点清单.txt](training_report/实际阶段与检查点清单.txt) |
| 实际训练配置、完成记录和血缘证据 | [training_report/TRAINING_EVIDENCE.json](training_report/TRAINING_EVIDENCE.json) |
| 站立ONNX | [policy/xc_standing.onnx](policy/xc_standing.onnx) |
| 原配API-v2站走消费者 | [policy/xc_walk_stand.py](policy/xc_walk_stand.py) |
| 选定完整PT | [checkpoints/feature_precise.pt](checkpoints/feature_precise.pt) |
| 冻结身体来源PT | [checkpoints/body_2700.pt](checkpoints/body_2700.pt) |
| PT推理与导出结构参考 | [inference/](inference/) |
| 整理报告下载包 | [training_report_bundle.zip](training_report_bundle.zip) |
| 文件范围和SHA-256 | [PACKAGE_MANIFEST.json](PACKAGE_MANIFEST.json) |

## 实际训练路线

```text
随机初始化
0–300     基础站立与恢复
300–1300  混合恢复任务，300轮后加入头部命令课程
1300–1800 共同收敛与交接稳定
1800–2200 最高难度推扰与DR
2200–2700 solver4联合微调，冻结归一化；实际LR3e-5
          2700时头部门控验收未通过，停止原调度
→ 30度门控修复224轮
→ 保护身体的头部专家576轮
→ 取消物理门控、仅站立任务续训512轮
→ HOME参考动作结构训练128轮
→ 指令特征缩放与±0.01rad修正候选选择（无新增PPO）
→ feature_precise.pt → ONNX → 当前v1版本
```

主训4096环境×20步/轮；所选修复为1024环境×20步/轮。修复链按 `completion.json` 的source/SHA确认，弃用分支和smoke没有计入。完整说明保留原始目录及物理模型来源，版本名称按当前“v2.0.2 v1”使用。

## 模型身份

| 文件 | SHA-256 |
|---|---|
| `policy/xc_standing.onnx` | `016f26b78f9c67226d695a3d57b176d36b4e57b381a3de77568ffd02f99fdbc3` |
| `policy/xc_walk_stand.py` | `c581d1ae712a57855cb60947ce97adaa104538c21ef5290115b70b8bb720ca04` |
| `checkpoints/feature_precise.pt` | `28efbd7d65457fb41cce6d63c4afbab54fc494801683577c4acfec5aef6f7dc6` |
| `checkpoints/body_2700.pt` | `843c90e92eeb3fb265af9d04a7f74f8adf33933847a83566aa7a54d506313a66` |

输入61维、输出14维，控制周期20ms。归一化及4次内部求解已在ONNX中，外部按增量解码。消费者为原配归档版；未采用后来尚未完成物理核准的角度转换候选。行走网络在 [../walk/](../walk/) 单独归档，本目录不附带行走权重。

## 验证状态与范围

- 特定仿真协议下做过头部跟随、身体恢复、推扰和交接评估；最终站稳与全程不倒的指标分开记录。
- 身体抖动、迁移极限范围及真机前倾/恢复卡住仍有未解决项，不标为完整实机验收通过。
- 电机角/模型角的实际物理对应尚未完成独立核准；本档案不能作为直接修改网页HOME、电机零位或放宽硬件限位的依据。
- 这里包含报告、33段配置/完成记录、关键源码摘录、最终PT和冻结身体PT；**未包含**全部中间checkpoint、完整owner/project、原始网格/状态库及CUDA依赖。它不是可解压后一键从零复训的完整环境。
- 配置和参考导出脚本保留原训练机绝对路径，迁移目录时需重新绑定。`inference_policy.py` 是原PT参考加载器；重现当前ONNX还应保留导出脚本中的HOME差值适配，不能只把PT当普通MLP加载。

在本目录做归档完整性检查，仅需Python标准库：

```bash
python3 tools/verify_archive.py
```

本次是只读整理和归档，没有启动训练或操作真机。
