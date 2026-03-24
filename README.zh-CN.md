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

## 功能

- 自动识别 `MediaCatalog.bytes` 的多种格式。
- 支持明文 JSON 识别。
- 支持单字节 XOR 尝试（`0x00` 到 `0xFF`）。
- 支持基于 `MediaCatalog.hash` 的循环 XOR 尝试（若该文件存在）。
- 支持二进制目录结构解析并恢复为 JSON。
- 仅在成功解析为有效结构时输出文件。
- 输出文件名包含密钥信息（如 `MediaCatalog_key_0x00_binary.json`）。
- 对结果做内容去重，避免重复输出。

## 环境要求

- Python 3.10+（推荐 3.11+）
- 不依赖第三方 Python 包

可选文件：

- `MediaCatalog.hash`（用于附加 hash-key 尝试）

## 目录要求

请将以下文件放在同一目录：

- `unlock.py`
- `MediaCatalog.bytes`
- `MediaCatalog.hash`（可选）

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

3. 到 `unlock` 目录查看输出结果。

## 输出命名规则

输出文件名会带上密钥信息，例如：

- `MediaCatalog_key_0x00_binary.json`
- `MediaCatalog_key_0x2A_json.json`
- `MediaCatalog_key_0x4D_0x14_0x88_0x21_binary.json`

含义说明：

- `0x00` 表示原始数据（XOR 不改变内容）。
- `json` 表示按 JSON 方式解析成功。
- `binary` 表示按二进制目录结构解析成功。

## 工作流程

脚本按以下顺序尝试恢复：

1. 直接将原始字节解析为 JSON。
2. 直接将原始字节按二进制目录结构解析。
3. 如果原始数据已命中，提前结束以提升速度。
4. 否则尝试社区常见密钥（`0x2A`、`0x13`、`0x37`、`0x59`）。
5. 再做单字节 XOR 全量暴力（`0x00` 到 `0xFF`）。
6. 若存在 hash 文件，尝试基于 hash 的循环 XOR（LE/BE）。

只有通过结构校验的结果才会被保存。

## 常见问题

- 报错：`MediaCatalog.bytes` not found
  - 请确认 `MediaCatalog.bytes` 与 `unlock.py` 位于同一目录。

- 没有任何输出
  - 输入文件可能使用了不同版本/格式。
  - 请检查文件完整性，并尽量使用匹配版本的资源文件。

- 输出看起来重复
  - 脚本会按内容去重。
  - 若两种方式得到同内容，通常只保留一份。

## 适用范围

本项目仅用于逆向学习、二进制格式研究与个人研究流程。
