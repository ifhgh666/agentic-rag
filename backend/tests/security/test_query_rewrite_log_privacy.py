"""Public rewrite telemetry must never copy local prompt/history diagnostics."""
import json
from types import SimpleNamespace
from uuid import uuid4

from app.observability.logger import StructuredLogger
from app.observability.diagnostics import DiagnosticRecorder
from tests.unit.test_diagnostics import wait_status
from langchain_core.messages import AIMessage
from app.core.pipeline import RagPipeline


def test_raw_diagnostics_stay_local_while_public_events_and_logs_are_safe(settings):
    private = "PRIVATE_HISTORY_SENTINEL"
    trace = {"node": "query_analysis", "model_call_id": "model-local", "timestamp_ns": 1, "duration_ms": 12,
             "provider": "ollama", "model": "scripted", "input_tokens": 20, "output_tokens": 8, "usage_source": "provider",
             "input_messages": [{"role": "system", "content": "SYSTEM_PROMPT_SENTINEL"}, {"role": "user", "content": private}],
             "candidate_content": "RAW_CANDIDATE_SENTINEL", "original_conditions": private,
             "tool_definitions": [{"description": "TOOL_SCHEMA_SENTINEL"}],
             "returned_tool_calls": [], "private_reasoning": "REASONING_SENTINEL",
             "api_key": "sk-synthetic-secret", "authorization": "Bearer synthetic-secret"}
    def frames(*args):
        observation = args[-1][0]
        observation.model_trace.append(trace)
        yield {'kind': 'custom', 'data': {'event': 'model_call', 'node': 'rewrite_query', 'details': trace}}
        yield {'kind': 'final', 'data': {'state': {'messages': [AIMessage(content='请说明型号。')]}, 'pending': True}}
    graph = SimpleNamespace(settings=settings, retriever=None, stream_run=frames)
    logger = StructuredLogger(settings.data_dir / "public.jsonl")
    recorder = DiagnosticRecorder(settings.data_dir / "logs/loop_traces")
    recorder.start()
    pipeline = RagPipeline(graph, logger, diagnostics=recorder)
    request_id = uuid4()
    try:
        events = list(pipeline.run("它的参数？", request_id, thread_id="privacy-thread"))
        job_id = next(event["data"]["details"]["diagnostic_id"] for event in events
                      if event["event"] == "node" and event["data"]["node"] == "diagnostics")
        assert wait_status(recorder, recorder.status(job_id)).status == "saved"
    finally:
        recorder.close()
    public = json.dumps(events, ensure_ascii=False) + logger.log_path.read_text(encoding="utf-8")
    for secret in (private, "SYSTEM_PROMPT_SENTINEL", "RAW_CANDIDATE_SENTINEL", "TOOL_SCHEMA_SENTINEL",
                   "REASONING_SENTINEL", "sk-synthetic-secret", "Bearer synthetic-secret"):
        assert secret not in public
    model = next(event["data"] for event in events if event["event"] == "model_call")
    assert model["model_call_id"] == "model-local" and model["duration_ms"] == 12
    assert model["details"]["input_tokens"] == 20
    local = json.loads((settings.data_dir / "logs/loop_traces" / f"{request_id}.json").read_text(encoding="utf-8"))
    assert local["model_trace"][0]["input_messages"][1]["content"] == private
    assert local["model_trace"][0]["candidate_content"] == "RAW_CANDIDATE_SENTINEL"
    assert "REASONING_SENTINEL" not in json.dumps(local) and "sk-synthetic-secret" not in json.dumps(local)


def test_nested_prompt_and_history_are_hidden_in_structured_logs(settings):
    logger = StructuredLogger(settings.data_dir / "nested.jsonl")
    logger.log("INFO", "rewrite-test", "synthetic metadata", details={"nested": {
        "input_messages": [{"content": "PRIVATE_MESSAGES_SENTINEL"}],
        "conversation_summary": "PRIVATE_SUMMARY_SENTINEL", "history_messages": ["PRIVATE_MESSAGES_SENTINEL"],
        "system_prompt": "SYSTEM_SENTINEL", "reasoning": "REASONING_SENTINEL", "api_key": "sk-synthetic-key"}})
    public = logger.log_path.read_text(encoding="utf-8")
    for secret in ("PRIVATE_MESSAGES_SENTINEL", "PRIVATE_SUMMARY_SENTINEL", "SYSTEM_SENTINEL", "REASONING_SENTINEL", "sk-synthetic-key"):
        assert secret not in public
