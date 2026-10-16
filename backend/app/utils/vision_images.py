import base64
import binascii
import hashlib
import struct
import zlib

from app.core.exceptions import BusinessRuleError
from app.core.storage import storage_path


def save_vision_image(task_id: int, encoded: str | None) -> str:
    try:
        raw = base64.b64decode(encoded or "", validate=True)
    except (ValueError, binascii.Error) as exc:
        raise BusinessRuleError("截图编码无效") from exc
    if not raw.startswith(b"\x89PNG\r\n\x1a\n") or not 8 < len(raw) <= 5 * 1024 * 1024:
        raise BusinessRuleError("截图必须为 5 MiB 以内的 PNG")
    directory = storage_path("screenshots")
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"vision_agent_{task_id}_{hashlib.sha256(raw).hexdigest()[:20]}.png"
    path = directory / filename
    path.write_bytes(raw)
    return str(path)


def red_test_image() -> bytes:
    def chunk(kind, data):
        return struct.pack("!I", len(data)) + kind + data + struct.pack("!I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack("!2I5B", 64, 64, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress((b"\0" + b"\xff\0\0" * 64) * 64)) + chunk(b"IEND", b""))
