from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..auth.service import AuthService
from ..dependencies import get_auth_service, require_user
from ..schemas.auth import LoginRequest, LoginResponse, SessionUser, UserInfo

router = APIRouter(prefix="/auth", tags=["身份认证"])
bearer = HTTPBearer(auto_error=False)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, auth: AuthService = Depends(get_auth_service)):
    token, expires_in, _ = auth.login(payload.username, payload.password)
    return LoginResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserInfo(username=payload.username),
    )


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    auth: AuthService = Depends(get_auth_service),
    _user: SessionUser = Depends(require_user),
):
    if credentials:
        auth.logout(credentials.credentials)
    return Response(status_code=204)

