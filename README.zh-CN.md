# MediaCatalog Unlocker（单文件 Python 工具）

**简体中文** | [English](README.md)

这是一个独立的 Python 工具，用于分析并恢复 Blue Archive 的 `MediaCatalog.bytes` 数据。

本项目按“单文件脚本”方式组织：

- `unlock.py`

## 声明

本工具仅用于学习与研究。

- 请勿用于非法传播、侵权或任何违法用途。
- 请勿分发游戏的受版权保护资源。
- 使用者需自行遵守所在地法律法规以及游戏发行方条款。


## 环境要求

- Python 3.10+（推荐 3.11+）
- 不依赖第三方 Python 包

可选文件：

- `MediaCatalog.hash`（用于附加 hash-key 尝试）

## 目录要求

请将以下文件放在同一目录：

- `unlock.py`
- `MediaCatalog.bytes`

脚本输出目录：

- `./unlock/`

## 快速开始

1. 创建并激活虚拟环境（可选，推荐）：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. 运行脚本：

```powershell
python unlock.py
```

## 适用范围

本项目仅用于逆向学习、二进制格式研究与个人研究流程。
