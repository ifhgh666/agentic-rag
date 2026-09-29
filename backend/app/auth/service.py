from datetime import datetime, timezone

from fastapi import HTTPException, status

from ..config import Settings
from .security import create_access_token, decode_access_token, verify_password


class AuthService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.revoked_tokens: dict[str, datetime] = {}

    def login(self, username: str, password: str) -> tuple[str, int, str]:
        if username != self.settings.admin_username or not verify_password(
            password, self.settings.admin_password_hash
        ):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="INVALID_CREDENTIALS")
        token, token_id, expires_in = create_access_token(
            username, self.settings.jwt_secret, self.settings.jwt_expire_minutes
        )
        return token, expires_in, token_id

    def logout(self, token: str) -> None:
        try:
            payload = decode_access_token(token, self.settings.jwt_secret)
            token_id = payload.get("jti")
            expires = payload.get("exp")
            if token_id:
                expiry = datetime.fromtimestamp(expires, tz=timezone.utc) if expires else datetime.now(timezone.utc)
                self.revoked_tokens[token_id] = expiry
        except Exception:
            return

    def authenticate(self, token: str) -> tuple[str, str]:
        try:
            payload = decode_access_token(token, self.settings.jwt_secret)
        except Exception as exc:
            raise HTTPException(status_code=401, detail="INVALID_TOKEN") from exc
        token_id = payload.get("jti", "")
        if token_id in self.revoked_tokens:
            raise HTTPException(status_code=401, detail="SESSION_REVOKED")
        username = payload.get("sub")
        if username != self.settings.admin_username or not token_id:
            raise HTTPException(status_code=401, detail="INVALID_TOKEN")
        return username, token_id

