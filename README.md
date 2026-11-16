# Xduck 设备代码

`main` 按设备整理源码；原 `main` 完整保存在 [`driver`](https://github.com/x-rangecraft/Xduck/tree/driver) 分支。

```text
121/
├── rk3566/
│   ├── microduck/                 # 完整 Rust workspace
│   ├── STM32_DMUSB_V4_PROTOCOL.md
│   └── SOURCE-SHA256SUMS
└── stm32/
    ├── stm32-h7-dm/                # STM32 H7 工程
    ├── SOURCE-SHA256SUMS
    └── PROVENANCE.json
122/
├── rk3566/
└── stm32/
124/
├── rk3566/
└── stm32/
125/
├── rk3566/
└── stm32/
```

121 已导入；122、124、125 当前为占位目录，尚未导入各自设备代码。

## 121 来源与核验

整理日期：2026-11-16（Asia/Shanghai）。

- RK3566：通过项目固定 SSH 配置，从身份核验通过的 121 设备 `/home/xduck1/xrange/10-source/rk3566/` 只读取得 `microduck/` 和 DMUSB v4 文档，共 331 个文件，下载后 SHA256 与设备逐文件一致。
- 121 当前安装的 Linux 版本为 `0.10.0-dev.local.1794380400.g90b1a18`。本目录归档设备当前源码镜像；未发现该安装版本的完整源码清单，不能把镜像与运行二进制宣称为逐字节可复现对应。
- STM32：121 设备上没有 STM32 源码目录，因此从本地烧录记录对应的 Git 提交 `90b1a189c21703cfb1dd8ed36ccf7c4b0833543e` 恢复工程。与 2026-10-24 clear-errors 烧录构建清单中的 1,166 个文件逐一核对，全部 SHA256 一致。来源细节见 `121/stm32/PROVENANCE.json`。
- 排除 RK3566 的 `target/`、版本库元数据、临时缓存及开发签名密钥目录。STM32 保留原厂 CMSIS 库依赖。

## 使用与后续维护

RK3566 workspace 入口为 `121/rk3566/microduck/Cargo.toml`；STM32 CMake 入口为 `121/stm32/stm32-h7-dm/CtrBoard-H7_ALL/CMakeLists.txt`。
源码自带的工程说明保留原文，其中 `10-source/`、`20-build/` 等路径描述原开发环境。历史完整工程规范、工具和脚本见 `driver` 分支的 `00-docs/ENGINEERING_WORKFLOW.md`。

本次仅重新整理、校验并上传源码，未编译、部署、烧录或操作电机。后续设备源码分别放入对应设备目录，避免跨设备混用配置、模型、标定和固件。
