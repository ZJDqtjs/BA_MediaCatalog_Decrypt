import json
import struct
from pathlib import Path
from typing import Any


COMMUNITY_KEYS = [0x2A, 0x13, 0x37, 0x59]


def xor_single_key(data: bytes, key: int) -> bytes:
    """单字节 XOR。"""
    return bytes(b ^ key for b in data)


def xor_repeating_key(data: bytes, key_bytes: bytes) -> bytes:
    """循环多字节 XOR。"""
    key_len = len(key_bytes)
    return bytes(b ^ key_bytes[i % key_len] for i, b in enumerate(data))


def try_parse_json(raw: bytes) -> Any | None:
    """尝试将字节解析为 JSON，成功返回对象，失败返回 None。"""
    text = raw.decode("utf-8", errors="strict")
    return json.loads(text)


def is_catalog_like_json(obj: Any) -> bool:
    """弱校验：命中 JSON 且结构像 MediaCatalog。"""
    return isinstance(obj, dict) and isinstance(obj.get("Table"), dict)


def _read_i32(data: bytes, pos: int) -> tuple[int, int]:
    if pos + 4 > len(data):
        raise ValueError("out of range while reading i32")
    return struct.unpack_from("<i", data, pos)[0], pos + 4


def _read_u32(data: bytes, pos: int) -> tuple[int, int]:
    if pos + 4 > len(data):
        raise ValueError("out of range while reading u32")
    return struct.unpack_from("<I", data, pos)[0], pos + 4


def _read_u64(data: bytes, pos: int) -> tuple[int, int]:
    if pos + 8 > len(data):
        raise ValueError("out of range while reading u64")
    return struct.unpack_from("<Q", data, pos)[0], pos + 8


def _read_len_string(
    data: bytes,
    pos: int,
    has_leading_marker: bool = False,
) -> tuple[str, int]:
    # 每个字符串前有一个 i32 标签值（通常是负数）和 u32 长度。
    if has_leading_marker:
        if pos + 1 > len(data):
            raise ValueError("out of range while reading marker")
        pos += 1

    _tag, pos = _read_i32(data, pos)
    slen, pos = _read_u32(data, pos)

    if slen > 65535:
        raise ValueError(f"invalid string length: {slen}")
    if pos + slen > len(data):
        raise ValueError("out of range while reading string bytes")

    raw = data[pos : pos + slen]
    pos += slen
    text = raw.decode("utf-8")
    return text, pos


def try_parse_binary_catalog(raw: bytes) -> dict[str, Any] | None:
    """
    解析新版 MediaCatalog.bytes 的二进制结构。

    推测记录结构（小端）：
      u8   version
      u32  count
      repeat count times:
        (i32 tag, u32 len, bytes key)
        (i32 tag, u32 len, bytes path)
        (i32 tag, u32 len, bytes filename)
        u64 bytes
        u32 crc
        u32 isPrologue(0/1)
        u32 mediaType
    """
    if len(raw) < 5:
        return None

    pos = 0
    version = raw[pos]
    pos += 1

    try:
        count, pos = _read_u32(raw, pos)
    except ValueError:
        return None

    # 基础合理性过滤。
    if version not in (1, 2):
        return None
    if count == 0 or count > 500000:
        return None

    table: dict[str, Any] = {}
    parsed = 0

    try:
        for _ in range(count):
            key, pos = _read_len_string(raw, pos)
            path, pos = _read_len_string(raw, pos, has_leading_marker=True)
            filename, pos = _read_len_string(raw, pos)
            byte_size, pos = _read_u64(raw, pos)
            crc, pos = _read_u32(raw, pos)
            is_prologue_u32, pos = _read_u32(raw, pos)
            media_type, pos = _read_u32(raw, pos)

            if not key or not path or not filename:
                return None
            if byte_size > 1024 * 1024 * 1024 * 64:
                return None
            if media_type > 64:
                return None

            item: dict[str, Any] = {
                "MediaType": media_type,
                "path": path,
                "FileName": filename,
                "Bytes": byte_size,
                "Crc": crc,
            }
            if is_prologue_u32 != 0:
                item["IsPrologue"] = True

            table[key] = item
            parsed += 1
    except (ValueError, UnicodeDecodeError, struct.error):
        return None

    # 解析成功率门槛，避免误判随机数据。
    if parsed < max(16, int(count * 0.8)):
        return None

    return {
        "Meta": {
            "Version": version,
            "Count": count,
            "Parsed": parsed,
        },
        "Table": table,
    }


def _read_ascii_run(raw: bytes, start: int) -> tuple[str, int]:
    pos = start
    while pos < len(raw):
        b = raw[pos]
        if 32 <= b <= 126:
            pos += 1
            continue
        break

    text = raw[start:pos].decode("ascii", errors="ignore")
    return text, pos


def _find_next_token(raw: bytes, start: int, tokens: list[bytes]) -> int:
    hits = [raw.find(t, start) for t in tokens]
    hits = [h for h in hits if h != -1]
    return min(hits) if hits else -1


def try_parse_binary_catalog_loose(raw: bytes) -> dict[str, Any] | None:
    """
    宽松提取器：基于字符串与字段邻接关系提取记录。
    适配结构小改版，优先保证能恢复可用索引。
    """
    key_prefix = [b"audio/", b"video/", b"scenario/", b"cafe/", b"uis/"]
    path_prefix = [b"GameData\\", b"Prologue\\"]

    pos = 0
    table: dict[str, Any] = {}
    safety = 0

    while pos < len(raw) - 64 and safety < 200000:
        safety += 1
        kpos = _find_next_token(raw, pos, key_prefix)
        if kpos == -1:
            break

        key, kend = _read_ascii_run(raw, kpos)
        if key.count("/") < 1 or len(key) < 6:
            pos = kpos + 1
            continue

        ppos = _find_next_token(raw, kend, path_prefix)
        if ppos == -1 or ppos - kend > 64:
            pos = kpos + 1
            continue

        path, pend = _read_ascii_run(raw, ppos)
        if "\\" not in path or len(path) < 8:
            pos = kpos + 1
            continue

        # 文件名通常紧跟在 path 之后不远处。
        name_candidate_start = raw.find(b".", pend, min(pend + 80, len(raw)))
        if name_candidate_start == -1:
            pos = kpos + 1
            continue

        # 回溯到文件名开头。
        nstart = name_candidate_start
        while nstart > pend and 32 <= raw[nstart - 1] <= 126 and raw[nstart - 1] not in (47, 92):
            nstart -= 1
        filename, nend = _read_ascii_run(raw, nstart)

        if "." not in filename or len(filename) < 4:
            pos = kpos + 1
            continue

        if nend + 20 > len(raw):
            break

        byte_size = struct.unpack_from("<Q", raw, nend)[0]
        crc = struct.unpack_from("<I", raw, nend + 8)[0]
        is_prologue = struct.unpack_from("<I", raw, nend + 12)[0]
        media_type = struct.unpack_from("<I", raw, nend + 16)[0]

        if byte_size == 0 or byte_size > 1024 * 1024 * 1024 * 64:
            pos = kpos + 1
            continue
        if media_type > 128:
            pos = kpos + 1
            continue

        item: dict[str, Any] = {
            "MediaType": media_type,
            "path": path,
            "FileName": filename,
            "Bytes": byte_size,
            "Crc": crc,
        }
        if is_prologue != 0:
            item["IsPrologue"] = True

        table[key] = item
        pos = nend + 20

    if len(table) < 100:
        return None

    return {
        "Meta": {
            "Mode": "loose-binary-extract",
            "Parsed": len(table),
        },
        "Table": table,
    }


def _looks_like_key_blob(blob: bytes) -> bool:
    try:
        s = blob.decode("ascii")
    except Exception:
        return False
    if len(s) < 6:
        return False
    return "/" in s and s[0].islower()


def _find_next_record_start(raw: bytes, pos: int, search_limit: int = 80) -> int:
    end = min(len(raw) - 12, pos + search_limit)
    for q in range(pos, end):
        try:
            tag = struct.unpack_from("<i", raw, q)[0]
            slen = struct.unpack_from("<I", raw, q + 4)[0]
        except struct.error:
            return -1

        if not (-4096 <= tag <= -1):
            continue
        if not (4 <= slen <= 256):
            continue

        s_start = q + 8
        s_end = s_start + slen
        if s_end > len(raw):
            continue
        if _looks_like_key_blob(raw[s_start:s_end]):
            return q
    return -1


def try_parse_binary_catalog_dynamic(raw: bytes) -> dict[str, Any] | None:
    """
    动态边界解析：前三个字符串按结构读取，尾部通过“下一条记录起点”反推。
    """
    if len(raw) < 5:
        return None

    pos = 0
    version = raw[pos]
    pos += 1
    try:
        count, pos = _read_u32(raw, pos)
    except ValueError:
        return None

    if version not in (1, 2):
        return None
    if count == 0 or count > 500000:
        return None

    table: dict[str, Any] = {}
    parsed = 0

    while pos < len(raw) - 32 and parsed < count:
        rec_start = pos
        try:
            key, pos = _read_len_string(raw, pos)
            # 第二个字符串前常有一个标记字节（如 0x07）
            path, pos = _read_len_string(raw, pos, has_leading_marker=True)
            filename, pos = _read_len_string(raw, pos)
        except Exception:
            break

        next_rec = _find_next_record_start(raw, pos)
        if next_rec == -1:
            # 最后一条记录：尽量使用剩余数据。
            next_rec = len(raw)

        trailer = raw[pos:next_rec]
        if len(trailer) < 12:
            pos = rec_start + 1
            continue

        byte_size = struct.unpack_from("<Q", trailer, 0)[0]
        crc = struct.unpack_from("<I", trailer, 8)[0]

        is_prologue = 0
        media_type = 0
        if len(trailer) >= 20:
            is_prologue = struct.unpack_from("<I", trailer, 12)[0]
            media_type = struct.unpack_from("<I", trailer, 16)[0]
        elif len(trailer) >= 16:
            # 某些版本尾部字段更短，保底读取 u16/u16。
            is_prologue = struct.unpack_from("<H", trailer, 12)[0]
            media_type = struct.unpack_from("<H", trailer, 14)[0]

        if not key or not path or not filename:
            pos = rec_start + 1
            continue
        if byte_size == 0 or byte_size > 1024 * 1024 * 1024 * 64:
            pos = rec_start + 1
            continue

        item: dict[str, Any] = {
            "MediaType": media_type,
            "path": path,
            "FileName": filename,
            "Bytes": byte_size,
            "Crc": crc,
        }
        if is_prologue != 0:
            item["IsPrologue"] = True

        table[key] = item
        parsed += 1
        pos = next_rec

    if parsed < 100:
        return None

    return {
        "Meta": {
            "Mode": "dynamic-binary-parse",
            "Version": version,
            "Count": count,
            "Parsed": parsed,
        },
        "Table": table,
    }


def load_hash_key_bytes(hash_path: Path) -> list[bytes]:
    """
    从 MediaCatalog.hash 读取整数，并生成常见 4 字节候选 key。
    返回候选列表：[little_endian, big_endian]
    """
    value = int(hash_path.read_text(encoding="utf-8").strip())
    little = value.to_bytes(4, byteorder="little", signed=False)
    big = value.to_bytes(4, byteorder="big", signed=False)
    return [little, big]


def decrypt_ba_mediacatalog_auto(
    input_path: str,
    output_dir: str,
    hash_path: str | None = None,
) -> list[str]:
    """
    自动探测并解密 Blue Archive MediaCatalog.bytes。
    策略：
    1) 直接当明文 JSON
    2) 直接按二进制 Catalog 结构解析
    3) 优先尝试社区常用单字节 XOR key
    4) 暴力枚举单字节 XOR key: 0x00~0xFF
    5) 若提供 hash 文件，尝试 4 字节循环 XOR (LE/BE)
    仅当结果可恢复为 JSON 结构时才保存。
    """
    input_file = Path(input_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    encrypted = input_file.read_bytes()
    saved_files: list[str] = []
    seen_payloads: set[str] = set()

    def _save_unique_json(parsed: Any, filename: str) -> bool:
        payload = json.dumps(parsed, ensure_ascii=False, sort_keys=True)
        if payload in seen_payloads:
            return False
        seen_payloads.add(payload)

        output_path = out_dir / filename
        output_path.write_text(
            json.dumps(parsed, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        saved_files.append(str(output_path))
        return True

    def save_if_json(candidate: bytes, filename: str) -> bool:
        try:
            parsed = try_parse_json(candidate)
        except Exception:
            return False

        if not is_catalog_like_json(parsed):
            return False
        return _save_unique_json(parsed, filename)

    def save_if_binary_catalog(candidate: bytes, filename: str) -> bool:
        parsed = try_parse_binary_catalog(candidate)
        if parsed is None:
            parsed = try_parse_binary_catalog_dynamic(candidate)
        if parsed is None:
            parsed = try_parse_binary_catalog_loose(candidate)
        if parsed is None:
            return False
        return _save_unique_json(parsed, filename)

    # 1) 已经是明文 JSON
    raw_json_hit = save_if_json(encrypted, "MediaCatalog_key_0x00_json.json")
    # 2) 直接按二进制 Catalog 解析
    raw_binary_hit = save_if_binary_catalog(encrypted, "MediaCatalog_key_0x00_binary.json")

    # 优化：原始数据已经命中时，通常无需继续全量暴力扫描。
    if raw_json_hit or raw_binary_hit:
        return saved_files

    # 3) 先尝试社区常见 key
    for key in COMMUNITY_KEYS:
        candidate = xor_single_key(encrypted, key)
        save_if_json(candidate, f"MediaCatalog_key_0x{key:02X}_json.json")
        save_if_binary_catalog(candidate, f"MediaCatalog_key_0x{key:02X}_binary.json")

    # 4) 单字节 XOR 暴力循环（0x00~0xFF）
    # 这里按你的要求显式用 0x 开头两位十六进制 key 进行尝试。
    for key in range(256):
        candidate = xor_single_key(encrypted, key)
        save_if_json(candidate, f"MediaCatalog_key_0x{key:02X}_json.json")
        save_if_binary_catalog(candidate, f"MediaCatalog_key_0x{key:02X}_binary.json")

    # 5) 使用 hash 的 4 字节循环 XOR
    if hash_path:
        key_candidates = load_hash_key_bytes(Path(hash_path))
        for kb in key_candidates:
            candidate = xor_repeating_key(encrypted, kb)
            key_tag = "_".join(f"0x{b:02X}" for b in kb)
            save_if_json(candidate, f"MediaCatalog_key_{key_tag}_json.json")
            save_if_binary_catalog(candidate, f"MediaCatalog_key_{key_tag}_binary.json")

    return saved_files


def main() -> None:
    base_dir = Path.cwd()
    input_path = base_dir / "MediaCatalog.bytes"
    hash_file = base_dir / "MediaCatalog.hash"
    output_dir = base_dir / "unlock"

    if not input_path.exists():
        raise FileNotFoundError(f"未找到输入文件: {input_path}")

    hash_path = str(hash_file) if hash_file.exists() else None
    saved = decrypt_ba_mediacatalog_auto(
        str(input_path),
        str(output_dir),
        hash_path,
    )

    if saved:
        print("暴力破解完成，命中可解析 JSON 的结果如下：")
        for p in saved:
            print(f"  - {p}")
    else:
        print("暴力破解完成，但未命中可解析 JSON 的结果，未保存任何输出。")


if __name__ == "__main__":
    main()