"""ASGI disconnect releases the queue reader without waiting for a model result."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from threading import Event
from types import SimpleNamespace

from app.api import chat
from app.schemas.chat import ChatRequest


def test_disconnect_wakes_blocked_reader_while_model_worker_is_still_running(monkeypatch):
    waiting, reader_exited, release_model, producer_exited = (Event() for _ in range(4))
    queues = []

    class ObservedQueue(Queue):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.reads = 0
            queues.append(self)

        def get(self, *args, **kwargs):
            self.reads += 1
            observe = self.reads == 2
            if observe:
                waiting.set()
            try:
                return super().get(*args, **kwargs)
            finally:
                if observe:
                    reader_exited.set()

    def run(*args, **kwargs):
        try:
            yield {'event': 'step', 'data': {'stage': 'query_receipt'}}
            assert release_model.wait(5)
            yield {'event': 'complete', 'data': {'status': 'completed'}}
        finally:
            producer_exited.set()

    async def exercise():
        response = chat.stream_chat(ChatRequest(question='Question', thread_id='disconnect'),
                                    _user=None, services=SimpleNamespace(pipeline=SimpleNamespace(run=run)))

        async def receive():
            assert await asyncio.to_thread(waiting.wait, 3)
            return {'type': 'http.disconnect'}

        sent = []

        async def send(message):
            sent.append(message)

        try:
            await asyncio.wait_for(response({'type': 'http', 'asgi': {'spec_version': '2.0'}}, receive, send), 4)
            assert any(message.get('body', b'').startswith(b'event: step') for message in sent)
            assert not release_model.is_set() and not producer_exited.is_set()
            assert await asyncio.to_thread(reader_exited.wait, 1), 'Disconnected queue reader remained blocked'
        finally:
            # Always unblock the old implementation too, so a failing regression
            # cannot leave asyncio.run waiting for its default executor forever.
            release_model.set()
            for queue in queues:
                queue.put_nowait(None)
            assert await asyncio.to_thread(producer_exited.wait, 3)
            assert await asyncio.to_thread(reader_exited.wait, 3)

    monkeypatch.setattr(chat, 'Queue', ObservedQueue)
    with ThreadPoolExecutor(max_workers=1) as worker:
        monkeypatch.setattr(chat, '_STREAM_EXECUTOR', worker)
        asyncio.run(exercise())
