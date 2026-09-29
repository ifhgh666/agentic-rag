import json
from uuid import uuid4

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from ..dependencies import get_services, require_user
from ..schemas.auth import SessionUser
from ..schemas.chat import ChatRequest

router = APIRouter(prefix="/chat", tags=["聊天"])


def _sse(event: dict) -> str:
    return f"event: {event['event']}\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"


@router.post("/stream")
def stream_chat(payload: ChatRequest, _user: SessionUser = Depends(require_user), services=Depends(get_services)):
    request_id = uuid4()
    thread_id = payload.thread_id or payload.conversation_id

    def generator():
        for event in services.pipeline.run(payload.question, request_id, thread_id=thread_id):
            yield _sse(event)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Request-ID": str(request_id)},
    )
