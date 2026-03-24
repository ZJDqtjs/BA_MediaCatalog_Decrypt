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

## Requirements

- Python 3.10+ (recommended: 3.11+)
- No third-party Python dependencies required

Optional:

- `MediaCatalog.hash` (for extra hash-based key attempts)

## File Layout

Place files in the same directory:

- `unlock.py`
- `MediaCatalog.bytes`

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


## Intended Use

This project is intended for reverse-engineering learning, binary format study, and personal research workflows only.
