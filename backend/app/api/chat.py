import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
from queue import Full, Queue
from threading import Event
from uuid import uuid4

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from ..dependencies import get_services, require_user
from ..schemas.auth import SessionUser
from ..schemas.chat import ChatRequest

router = APIRouter(prefix="/chat", tags=["聊天"])
_STREAM_EXECUTOR = ThreadPoolExecutor(max_workers=8, thread_name_prefix="rag-stream")


def _sse(event: dict) -> str:
    return f"event: {event['event']}\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"


@router.post("/stream")
def stream_chat(payload: ChatRequest, _user: SessionUser = Depends(require_user), services=Depends(get_services)):
    request_id = uuid4()
    thread_id = payload.thread_id or payload.conversation_id or f"thread-{uuid4()}"

    async def generator():
        queue = Queue(maxsize=128)
        closed = Event()
        events = services.pipeline.run(payload.question, request_id, thread_id=thread_id, action=payload.action)

        def put(value):
            while not closed.is_set():
                try:
                    queue.put(value, timeout=0.1)
                    return
                except Full:
                    continue

        def pump():
            try:
                for event in events:
                    if closed.is_set():
                        break
                    put(event)
            except Exception:
                identity = {"request_id": str(request_id), "thread_id": thread_id}
                put({"event": "error", "data": {**identity, "code": "RAG_PIPELINE_FAILED", "message": "问答处理失败。"}})
                put({"event": "complete", "data": {**identity, "status": "failed"}})
            finally:
                events.close()
                put(None)

        _STREAM_EXECUTOR.submit(pump)
        try:
            while True:
                event = await asyncio.to_thread(queue.get)
                if event is None:
                    return
                yield _sse(event)
                if event["event"] == "complete":
                    return
        finally:
            # No product timer is imposed. A disconnected reader stops consuming;
            # the worker closes its graph iterator once the current SDK call yields.
            closed.set()
            # Cancelling to_thread does not stop queue.get in its executor.
            # Wake that reader even while the SDK worker is still blocked.
            try:
                queue.put_nowait(None)
            except Full:
                pass  # A full queue cannot have a reader blocked on an empty one.

    return StreamingResponse(generator(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Request-ID": str(request_id)})
