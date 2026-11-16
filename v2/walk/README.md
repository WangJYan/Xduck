# v2行走：2.0.2机体，累计3142更新的柔性模型

归档日期：2026-11-16。最终文件与桌面 `v3/P12_flexDR100.onnx` 一致。

ONNX SHA-256：`40c392fa41a30c657ca21528151120fa877983ad906181ef98c29985a17c2d20`。

这是原实际 UniLab/Warp 训练链路的归档，包含源码快照、关键检查点、训练数据和物理资产；没有声称已迁移为本仓库新版UniLab任务，也没有声称已完成真机验收。

## 文件入口

| 内容 | 位置 |
|---|---|
| 最终Walk ONNX | [policy/P12_flexDR100.onnx](policy/P12_flexDR100.onnx) |
| 原配API-v2站走消费者 | [policy/xc_walk_stand.py](policy/xc_walk_stand.py) |
| 完整训练过程 | [training_report/v2.0.2_v1柔性行走模型_完整训练过程.html](training_report/v2.0.2_v1柔性行走模型_完整训练过程.html) |
| 训练机实际各阶段配置与完成记录 | [training_report/REMOTE_TRAINING_EVIDENCE.json](training_report/REMOTE_TRAINING_EVIDENCE.json) |
| 最后100轮生效配置 | [training_report/EFFECTIVE_CONFIG.yaml](training_report/EFFECTIVE_CONFIG.yaml) |
| 最终导出记录 | [training_report/EXPORT_METADATA.json](training_report/EXPORT_METADATA.json) |
| 每个文件SHA-256及归档范围 | [PACKAGE_MANIFEST.json](PACKAGE_MANIFEST.json) |
| 档案完整性检查 | `uv run --no-project python tools/verify_archive.py` |

报告沿用用户的“v1柔性行走”内部称呼；本仓库按用户本次要求将其归入 `v2/walk/`，两者是同一个3142更新模型。HTML下载后用浏览器打开可观看相对路径视频；GitHub网页不直接渲染HTML。

## 选用训练血缘

```text
2.0.2机体随机初始化
P00 200 → P01 701 → P02 299 → P03 30
→ P05 81 → P06 151
→ 800步后退bootstrap → P07 180                 累计1642次PPO
→ 固定10cm目标：P09 400 → P10 200
→ 1800步BC → P11 400 → P12 400                累计3042次PPO
→ 从P12末尾恢复权重/Adam，柔性＋柔性DR续训100次  累计3142次PPO
```

P04、P08移除；P13没有作为本模型父节点。800步bootstrap和1800步BC属于监督更新，不另加到3142次PPO中。P05实际256环境、P06/P07实际128环境；其余所选阶段及柔性续训为4096环境，均24步rollout。

最后100轮使用48个被动柔性轴，刚度按部件为100～1500N·m/rad、阻尼3N·m·s/rad；每次重置各柔性轴刚度/阻尼独立±10%。14主动轴、actor61维、critic76维。保持原P12奖励/10cm目标、LR3e-5、5epochs/32minibatches、anchor0.002，并冻结actor归一化。20ms策略周期、1ms电机周期、每电机周期16个62.5μs物理步。96个独立沉降世界×3快照形成288条柔性站立库。

## 训练材料与原样恢复

三个归档均小于GitHub单文件100MiB限制，无需Git LFS：

- `archives/rigid_lineage_checkpoints_and_sources.tar.gz`：P00～P12选用的11个关键checkpoint、各阶段配置/完成记录/可用anchor与seed、阶段脚本和owner源码、原站立库、主线调度工具。另保留原祖先分支P07正式800步报告和seed；继承分支中同名的预检fixture报告不能当作正式800步证据。
- `archives/flex_continuation_runtime.tar.gz`：最终柔性分支的workspace/project源码、配置、物理XML/网格、输入父checkpoint/anchor/柔性站立库、续训tools、最终 `runs/P12/ppo_run/flex_update_100.pt` 及完成记录。排除缓存和中间重复checkpoint。
- `archives/effective_training.mjb.gz`：最终训练使用的精确compiled MJB，解压后的SHA为 `82a74a5eb50786bd7c219b29bb0ee27b47724533856dc33766dc20daf6b27ab9`。

在全新空目录恢复，勿覆盖已有训练输出：

```bash
mkdir -p restored/flex restored/rigid
# 下列命令在v2/walk目录执行
tar -xzf archives/flex_continuation_runtime.tar.gz -C restored/flex
gzip -dc archives/effective_training.mjb.gz > restored/flex/physics/effective_training.mjb
tar -xzf archives/rigid_lineage_checkpoints_and_sources.tar.gz -C restored/rigid
```

这是**训练现场快照**，保留原 `/home/xingchen/...` 路径以便审计。任意新路径恢复后，需要修正配置、脚本、XML中指向原工作区的绝对路径，并准备对应依赖；不能把解压成功当作已验证一键复训。最终continuation快照含该阶段完整project源码；刚性早期部分保存阶段脚本/owner而非每阶段重复完整工程。部分早期运行/依赖还需参考原工作区或v1历史归档。报告包自身的“未包含checkpoint/网格”范围仅针对 `training_report/`，本目录额外的三份archives补充了这些材料。

原训练机分支：

- `xduck_2_0_2_v201route_step13_20261108`：早期P00～P07的实际祖先。
- `xduck_2_0_2_v201route_step10_fromP07_20261109`：继承P07，按10cm目标重训P09～P12。
- `xduck_2_0_2_P12_flexDR100_20261114`：P12之后新增100次柔性续训。

归档内旧route_plan的路径/历史checkpoint说明有遗留值；实际选用记录以 `REMOTE_TRAINING_EVIDENCE.json`、checkpoint元数据、各阶段完成记录和文件SHA为准，不按模板里的旧2.0.1路径或P13计划推断本模型血缘。

## 结果与限制

同一最终视频轨迹前进17个有效交替步，单步中位11.52cm；10cm是目标值。训练日志的4.44/4.43cm是全部环境缓存均值，不能当成纯前进单步。前进视频Walk段平均约0.350m/s；训练混合任务日志0.136m/s不是同一统计口径。

名义柔性物理播放的前进、后退、左右转均未出现严重倾倒事件，但前进全段偏航+37.8°、后退−25.6°，转弯伴随位移；没有证明真机后仰原因已解决或多种子DR验收通过。视频和逐步测量见 `training_report/evidence/`。

部署时使用配套消费者与Walk ONNX，ONNX已内嵌归一化；消费者同时含旧站立接口但不含站立网络。本归档未提供重新训练的2.0.2站立模型。设备零位、IMU外参、实际增益/限位及反馈时序仍需按实体核对。
