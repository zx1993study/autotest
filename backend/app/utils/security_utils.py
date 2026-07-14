from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any


PBKDF2_ALGORITHM = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 260_000


def hash_password(password: str) -> str:
    """Hash a password with bcrypt when available.

    ``bcrypt`` is the production target and is declared in requirements. The
    PBKDF2 fallback keeps local development usable before dependencies are
    refreshed, while retaining salted one-way hashes instead of plaintext.
    """

    try:
        import bcrypt
    except ModuleNotFoundError:
        salt = os.urandom(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
        return "$".join(
            [
                PBKDF2_ALGORITHM,
                str(PBKDF2_ITERATIONS),
                _urlsafe_b64encode(salt),
                _urlsafe_b64encode(digest),
            ]
        )
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Return whether a plaintext password matches the stored hash."""

    if password_hash.startswith("$2"):
        try:
            import bcrypt
        except ModuleNotFoundError:
            return False
        return bool(bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8")))
    if password_hash.startswith(f"{PBKDF2_ALGORITHM}$"):
        return _verify_pbkdf2_password(password, password_hash)
    return False


def create_access_token(
    claims: dict[str, Any],
    secret_key: str,
    expires_in_seconds: int,
) -> str:
    """Create an HS256 JWT access token with an expiration timestamp."""

    now = int(time.time())
    payload = {**claims, "iat": now, "exp": now + expires_in_seconds}
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = ".".join(
        [
            _urlsafe_b64encode(json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode("utf-8")),
            _urlsafe_b64encode(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")),
        ]
    )
    signature = _sign(signing_input, secret_key)
    return f"{signing_input}.{signature}"


def verify_access_token(token: str, secret_key: str) -> dict[str, Any]:
    """Validate an HS256 JWT and return its claims.

    Raises:
        ValueError: If the token is malformed, expired, or has a bad signature.
    """

    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Token 格式不正确")
    signing_input = ".".join(parts[:2])
    expected_signature = _sign(signing_input, secret_key)
    if not hmac.compare_digest(expected_signature, parts[2]):
        raise ValueError("Token 签名无效")
    payload = _decode_json(parts[1])
    exp = payload.get("exp")
    if not isinstance(exp, int) or exp < int(time.time()):
        raise ValueError("Token 已过期")
    return payload


def _verify_pbkdf2_password(password: str, password_hash: str) -> bool:
    parts = password_hash.split("$")
    if len(parts) != 4:
        return False
    _, iterations_text, salt_text, digest_text = parts
    try:
        iterations = int(iterations_text)
        salt = _urlsafe_b64decode(salt_text)
        expected_digest = _urlsafe_b64decode(digest_text)
    except (TypeError, ValueError):
        return False
    actual_digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual_digest, expected_digest)


def _decode_json(value: str) -> dict[str, Any]:
    try:
        decoded = _urlsafe_b64decode(value).decode("utf-8")
        payload = json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError("Token 载荷无效") from exc
    if not isinstance(payload, dict):
        raise ValueError("Token 载荷无效")
    return payload


def _sign(signing_input: str, secret_key: str) -> str:
    signature = hmac.new(secret_key.encode("utf-8"), signing_input.encode("utf-8"), hashlib.sha256).digest()
    return _urlsafe_b64encode(signature)


def _urlsafe_b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _urlsafe_b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))
