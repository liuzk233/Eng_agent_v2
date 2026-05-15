import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID


def constant_time_equal(left: str, right: str) -> bool:
    return secrets.compare_digest(left, right)


def hash_invite_code(code: str) -> str:
    normalized = code.strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 210_000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, salt, expected = password_hash.split("$", 2)
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 210_000)
    return constant_time_equal(digest.hex(), expected)


def _base64url_encode(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")


def _base64url_decode(payload: str) -> bytes:
    padded = payload + "=" * (-len(payload) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def create_access_token(user_id: UUID, secret: str, expires_delta: timedelta = timedelta(hours=24)) -> str:
    issued_at = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": int(issued_at.timestamp()),
        "exp": int((issued_at + expires_delta).timestamp()),
    }
    body = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    return f"{body}.{_base64url_encode(signature)}"


def decode_access_token(token: str, secret: str) -> UUID | None:
    try:
        body, signature = token.split(".", 1)
        expected = hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
        if not constant_time_equal(_base64url_encode(expected), signature):
            return None
        payload = json.loads(_base64url_decode(body))
        if int(payload["exp"]) < int(datetime.now(timezone.utc).timestamp()):
            return None
        return UUID(str(payload["sub"]))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
