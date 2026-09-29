from fastapi import APIRouter, Depends

from ..dependencies import get_services, require_user
from ..schemas.auth import SessionUser
from ..schemas.chat import RetrieveRequest

router = APIRouter(prefix="/debug", tags=["检索诊断"])


@router.post("/retrieve")
def retrieve(payload: RetrieveRequest, _user: SessionUser = Depends(require_user), services=Depends(get_services)):
    results = services.retriever.search(payload.query, payload.top_k, payload.min_score)
    return {"query": payload.query, "results": [item.model_dump(mode="json", exclude={"text"}) for item in results]}

