# MediaCatalog Unlocker (Single Python File)

[简体中文](README.zh-CN.md) | **English**

A standalone Python tool to analyze and recover Blue Archive MediaCatalog data from `MediaCatalog.bytes`.

This project is designed as a single-file script:

- `unlock.py`

## Disclaimer

This tool is provided for learning and research purposes only.

- Do not use it for illegal distribution or infringement.
- Do not redistribute proprietary game assets.
- You are responsible for complying with local laws and the game publisher's terms.

## Features

- Auto-detects multiple formats from `MediaCatalog.bytes`.
- Supports plain JSON detection.
- Supports single-byte XOR attempts (`0x00` to `0xFF`).
- Supports hash-based repeating-key XOR attempts (if `MediaCatalog.hash` exists).
- Supports binary catalog parsing and recovery to JSON.
- Saves output only when valid structured data is recovered.
- Adds key information into output file names (example: `MediaCatalog_key_0x00_binary.json`).
- Deduplicates identical results.

## Requirements

- Python 3.10+ (recommended: 3.11+)
- No third-party Python dependencies required

Optional:

- `MediaCatalog.hash` (for extra hash-based key attempts)

## File Layout

Place files in the same directory:

- `unlock.py`
- `MediaCatalog.bytes`
- `MediaCatalog.hash` (optional)

The script writes results to:

- `./unlock/`

## Quick Start

1. Create and activate a virtual environment (optional but recommended):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Run the script:

```powershell
python unlock.py
```

3. Check output files in `unlock` folder.

## Output Naming

Output file names include key information:

- `MediaCatalog_key_0x00_binary.json`
- `MediaCatalog_key_0x2A_json.json`
- `MediaCatalog_key_0x4D_0x14_0x88_0x21_binary.json`

Meaning:

- `0x00` means raw data (no XOR effect).
- `json` means parsed as JSON.
- `binary` means parsed from binary catalog structure.

## How It Works

The script tries recovery in this order:

1. Parse raw bytes as JSON.
2. Parse raw bytes as binary catalog.
3. If raw hit is successful, stop early for speed.
4. Otherwise, try community keys (`0x2A`, `0x13`, `0x37`, `0x59`).
5. Try full single-byte XOR brute-force (`0x00` to `0xFF`).
6. If hash file exists, try repeating-key XOR from hash value (LE/BE).

Only valid parsed structures are saved.

## Troubleshooting

- Error: `MediaCatalog.bytes` not found
  - Put `MediaCatalog.bytes` in the same folder as `unlock.py`.

- No output generated
  - Input may use a different format/version.
  - Verify file integrity and try with matching version of catalog data.

- Output looks duplicated
  - The script deduplicates by content.
  - If two methods produce same content, only one result is kept.

## Intended Use

This project is intended for reverse-engineering learning, binary format study, and personal research workflows only.
