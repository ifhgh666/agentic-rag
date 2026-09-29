from fastapi import APIRouter, Depends, HTTPException, Query

from ..dependencies import get_services, require_user
from ..schemas.auth import SessionUser
from ..schemas.logs import LogListResponse

router = APIRouter(prefix="/logs", tags=["日志"])


@router.get("", response_model=LogListResponse)
def list_logs(
    level: str | None = Query(default=None),
    module: str | None = Query(default=None),
    request_id: str | None = Query(default=None),
    thread_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    _user: SessionUser = Depends(require_user),
    services=Depends(get_services),
):
    if level and level.upper() not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
        raise HTTPException(status_code=422, detail="INVALID_LOG_LEVEL")
    items = services.logger.query(level=level, module=module, request_id=request_id, thread_id=thread_id, limit=limit)
    return LogListResponse(items=items, count=len(items))
