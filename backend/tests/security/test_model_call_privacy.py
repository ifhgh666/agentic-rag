import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.observability.logger import StructuredLogger
from app.core.pipeline import RagPipeline
from langchain_core.messages import AIMessage
from app.core.model_call import ModelCallRunner, CallSpec
from app.core.model_provider import ModelResult
from tests.fakes.providers import ScriptedModel
from tests.unit.test_model_call_governance import active_context


@pytest.mark.parametrize("mode", ["completed", "provider_failed", "rejected"])
def test_public_projection_hides_private_call_bodies_and_attempts(settings, mode):
    context = active_context(settings)
    provider = ScriptedModel(ModelResult("PRIVATE_FIRST_REPLY_SENTINEL", "fake", "script"))
    if mode == "provider_failed":
        def fail(*args, **kwargs):
            raise OSError("PRIVATE_EXCEPTION_SENTINEL")
        provider.complete = fail
    if mode == "rejected":
        context.budget.finish(context.request_id)
    outcome = ModelCallRunner(settings, provider).invoke(CallSpec("orchestrator",
        [{"role": "user", "content": "PRIVATE_INPUT_SENTINEL"}],
        tools=[{"type": "function", "function": {"name": "test", "description": "PRIVATE_SCHEMA_SENTINEL"}}]), context)
    trace = outcome.record.to_trace()
    assert trace["input_messages"][0]["content"] == "PRIVATE_INPUT_SENTINEL"
    if mode == "completed":
        assert trace["candidate_content"] == "PRIVATE_FIRST_REPLY_SENTINEL"
    def frames(*args):
        if trace['attempted']:
            yield {'kind': 'custom', 'data': {'event': 'model_call', 'node': 'orchestrator', 'details': trace}}
        yield {'kind': 'final', 'data': {'state': {'messages': [AIMessage(content='请说明型号。')]}, 'pending': True}}
    graph = SimpleNamespace(settings=settings, retriever=None, stream_run=frames)
    logger = StructuredLogger(settings.data_dir / 'public.jsonl')
    events = list(RagPipeline(graph, logger).run('question', uuid4(), thread_id='privacy-thread'))
    public = json.dumps(events) + logger.log_path.read_text(encoding="utf-8")
    for private in ("PRIVATE_FIRST_REPLY_SENTINEL", "PRIVATE_INPUT_SENTINEL", "PRIVATE_SCHEMA_SENTINEL", "PRIVATE_EXCEPTION_SENTINEL"):
        assert private not in public
    assert "attempts" not in public
