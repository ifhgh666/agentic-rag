from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .auth.service import AuthService
from .schemas.auth import SessionUser

bearer = HTTPBearer(auto_error=False)


def get_services(request: Request):
    return request.app.state.services


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.services.auth


def require_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> SessionUser:
    if credentials is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="AUTHENTICATION_REQUIRED")
    username, token_id = auth.authenticate(credentials.credentials)
    return SessionUser(username=username, token_id=token_id)

