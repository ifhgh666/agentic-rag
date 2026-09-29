import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt

try:
    from pwdlib import PasswordHash

    _password_hasher = PasswordHash.recommended()
except Exception:  # pragma: no cover - only used when optional dependency is absent
    _password_hasher = None


def hash_password(password: str) -> str:
    if _password_hasher:
        return _password_hasher.hash(password)
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 180_000)
    return "pbkdf2$180000$%s$%s" % (salt.hex(), digest.hex())


def verify_password(password: str, encoded: str) -> bool:
    if not encoded:
        return False
    if encoded.startswith("pbkdf2$"):
        try:
            _, rounds, salt_hex, digest_hex = encoded.split("$", 3)
            digest = hashlib.pbkdf2_hmac(
                "sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds)
            )
            return hmac.compare_digest(digest.hex(), digest_hex)
        except (ValueError, TypeError):
            return False
    if _password_hasher:
        try:
            return _password_hasher.verify(password, encoded)
        except Exception:
            return False
    return False


def create_access_token(username: str, secret: str, expires_minutes: int) -> tuple[str, str, int]:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=expires_minutes)
    token_id = str(uuid4())
    payload = {"sub": username, "jti": token_id, "iat": now, "exp": expires}
    return jwt.encode(payload, secret, algorithm="HS256"), token_id, expires_minutes * 60


def decode_access_token(token: str, secret: str) -> dict:
    return jwt.decode(token, secret, algorithms=["HS256"])

