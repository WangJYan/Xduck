# Rider Mini · rk3566

设备编号 **125** 的 RK3566 Linux 上位机工程，沿用 `driver` 分支的八个工程分区。

- [工程目录与流程](00-docs/ENGINEERING_WORKFLOW.md)
- [源码工程](10-source/xduck/)
- [来源记录](00-docs/PROVENANCE.json)
- [当前源码校验清单](00-docs/SOURCE-SHA256SUMS)
- [部署入口说明](40-deploy/README.md)

```text
00-docs/       工程说明、来源与校验记录
10-source/     完整源码工程
20-build/      构建缓存
30-artifacts/  交付产物
40-deploy/     发布与部署说明
50-logs/       build / test / deploy 日志
60-tools/      工程检查工具
90-temp/       临时文件
```

从本目录运行 `./60-tools/check-layout.sh` 检查目录和源码哈希。构建参数与设备差异见 [设备说明](../README.md)。
