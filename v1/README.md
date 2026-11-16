# XDuck1：第一版机器人

本目录保存第一版XDuck1机器人的仿真、训练工程、策略模型和实验记录。

## 训练任务

| 目录 | 内容 |
|---|---|
| [walk/](walk/) | GF43X40行走工程，包含训练入口、物理资产、1975检查点和策略资料 |
| [stand/](stand/) | GF43X40走停与站立工程，包含599检查点和策略资料 |
| [sitstand/](sitstand/) | 坐站训练，包含2000→2500续训、2倍DR、源码、检查点及视频 |
| [walk_narrow_stance/](walk_narrow_stance/) | 缩小站距的行走训练，从零到最终柔性适配模型的完整选用主线 |
| [恢复站/](恢复站/) | 倒地恢复站立训练，包含0→3150更新过程、检查点和受控对照 |

## 行走与站立工程入口

`walk`、`stand` 使用UniLab `main@447e5ce`（1.3.1）的Manager-Based任务、UniSim MuJoCo后端和`uni_rl` PPO。两个工程各自提供`pyproject.toml`、`uv.lock`、任务代码、配置与模型资产。

```bash
# 在v1目录下进入行走工程
cd walk
uv sync --locked
uv run python -m unilab.scripts.train_rsl_rl --config-path "$PWD/conf/ppo"
```

```bash
# 在v1目录下进入站立工程
cd stand
uv sync --locked
uv run xduck-stand-train
```

两个工程固定相同的UniLab提交及`unisim-core==1.7.3`、`mjbatch-uni==0.2.1`、`torch==2.8.0`、`rsl-rl-lib==5.0.1`、`tensordict==0.11.0`。`stand`通过相邻的`walk`包共用GF电机实现。

## 训练记录与验证范围

各任务保存实际选用的检查点、配置、源码快照和证据。坐站、缩小站距行走、恢复站包含UniLab/Warp训练现场资料，其运行依赖及恢复方式见各任务README。

`walk`的1975检查点和`stand`的599检查点通过严格加载检查，但物理、足部传感器、接触时长、落脚奖励和部分DR/课程语义尚未全部完成数值等价验证。坐站、缩小站距行走及恢复站的性能结果也分别保留在任务记录中；工程运行通过不表示已完成实机验收。
