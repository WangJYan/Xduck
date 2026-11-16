# 电机模型

[gf43x40](gf43x40/) 是 GF43X40-10 电机模型的 UniLab 迁移包，原目录名为 `gf43x40_final_unilab_port_20260921`。模型版本为 `shared_fixed_gain_kd_band_v8_torque_proxy`。

- [迁移与接入说明](gf43x40/README_CN.md)：依赖、安装、自检和物理子步接入方式。
- [模型结构](gf43x40/MODEL_DETAILS_CN.md)、[参数](gf43x40/reference/PARAMETERS_CN.md)和[验证报告](gf43x40/reference/RESULTS.md)。
- `gf43x40/MANIFEST.json` 保存包内文件哈希；包内文件保持原样。

在迁移包目录运行独立自检：

```bash
cd motor/gf43x40
uv run --with numpy --with pytest python -I verify_port.py
```

模型参数是等效仿真标定值；迁移自检不能代替目标机器人整机验证。
