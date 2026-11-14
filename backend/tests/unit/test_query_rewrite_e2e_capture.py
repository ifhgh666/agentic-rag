"""Normal-API capture guards, using HTTP stubs and temporary files only."""
import json
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from app.config import Settings
from scripts.capture_query_rewrite_e2e import capture_run, load_requests, fingerprint, login_hidden

FIXTURE = Path(__file__).parents[1] / "fixtures/query_rewrite_v1_cases.json"


def profile(tmp_path):
    return Settings(_env_file=None, data_dir=tmp_path / "data", llm_provider="ollama",
                    ollama_model="qwen3:4b-instruct", embedding_backend="fastembed")


def review(entrance="passed", answer="passed"):
    return {"entrance_status": entrance, "answer_status": answer,
            "reviewer": "scripted_manual_stub", "rationale": "Test gate only; no semantic quality assertion."}


def body(status="completed", include_usage=True):
    events = [("analysis", {"is_clear": status != "clarification", "questions": ["raw question"]}),
              ("answer", {"answer": "first unmodified answer", "sources": [{"filename": "synthetic.pdf"}]}),
              ("verification", {"citation_status": "verified", "numeric_status": "not_evaluated"})]
    if include_usage:
        events.append(("usage", {"model_calls": 2, "tool_calls": 1, "cloud_calls": 0,
                                  "prompt_tokens": 30, "completion_tokens": 10, "usage_source": "provider"}))
    events.append(("complete", {"status": status, "reason": "timeout" if status == "failed" else None}))
    return "".join(f"event: {event}\ndata: {json.dumps(data)}\n\n" for event, data in events)


def client_for(responses, calls):
    iterator = iter(responses)

    def handler(request):
        calls.append(json.loads(request.content))
        response = next(iterator)
        if isinstance(response, Exception):
            raise response
        return httpx.Response(200, text=response, headers={"x-request-id": str(uuid4()),
                                                          "content-type": "text/event-stream"})
    return httpx.Client(base_url="http://127.0.0.1:8000", transport=httpx.MockTransport(handler))


def test_exact_three_questions_and_no_reference_input(tmp_path):
    assert [item["id"] for item in load_requests(FIXTURE)] == ["Q16", "C-UV", "COMPARE"]
    assert "设备输入电压为 245 V，持续 400 ms" in load_requests(FIXTURE)[0]["question"]
    calls = []
    with client_for([body()] * 3, calls) as client:
        summary = capture_run(client=client, settings=profile(tmp_path), cases_path=FIXTURE,
                              output=tmp_path / "run", reviewer=lambda *_: review())
    assert summary["status"] == "completed" and summary["model_calls"] == 6
    assert len(calls) == len({item["thread_id"] for item in calls}) == 3
    assert all(set(item) == {"question", "thread_id", "action"} and item["action"] == "new_question" for item in calls)
    assert all("reference" not in json.dumps(item) and "expected" not in json.dumps(item) for item in calls)


def test_manual_failure_keeps_raw_answer_and_stops_before_second_request(tmp_path):
    calls = []

    def inspect(record, case):
        assert (tmp_path / "run" / f"{case['id']}.raw.json").exists()
        assert record["answer"] == "first unmodified answer"
        assert record["verification"]["numeric_status"] == "not_evaluated"
        return review(answer="failed")

    with client_for([body()], calls) as client:
        summary = capture_run(client=client, settings=profile(tmp_path), cases_path=FIXTURE,
                              output=tmp_path / "run", reviewer=inspect)
    assert len(calls) == 1 and summary["stop_case"] == "Q16"
    assert [item["status"] for item in summary["cases"]] == ["failed", "not_run", "not_run"]
    assert (tmp_path / "run/Q16.sse.txt").read_text(encoding="utf-8") == body()


@pytest.mark.parametrize("response,reason", [(body("clarification"), "complete_answer_not_verified"),
                                            (body("failed"), "timeout"),
                                            (body(include_usage=False), "usage_unavailable"),
                                            ("event: answer\ndata: bad JSON\n\n", "invalid_sse"),
                                            (httpx.ReadTimeout("secret transport details"), "ReadTimeout")])
def test_incomplete_or_unknown_result_never_continues(tmp_path, response, reason):
    calls = []
    with client_for([response], calls) as client:
        summary = capture_run(client=client, settings=profile(tmp_path), cases_path=FIXTURE,
                              output=tmp_path / "run", reviewer=lambda *_: review(answer="not_verified"))
    assert len(calls) == 1 and summary["stop_reason"] == reason
    assert all(item["status"] == "not_run" for item in summary["cases"][1:])
    assert "secret transport details" not in (tmp_path / "run/Q16.raw.json").read_text(encoding="utf-8")
    if reason in {"usage_unavailable", "ReadTimeout", "invalid_sse"}:
        assert summary["model_calls"] is None  # Unknown is not zero.


def test_refuses_output_and_changed_fixture_before_post(tmp_path):
    calls = []
    output = tmp_path / "run"
    output.mkdir()
    with client_for([], calls) as client:
        with pytest.raises(FileExistsError):
            capture_run(client=client, settings=profile(tmp_path), cases_path=FIXTURE,
                        output=output, reviewer=lambda *_: review())
    assert not calls
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    next(item for item in data["cases"] if item["id"] == "RW24")["requests"].reverse()
    changed = tmp_path / "changed.json"
    changed.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="frozen_request"):
        load_requests(changed)


def test_index_file_changes_stop_batch_without_altering_evidence(tmp_path):
    settings = profile(tmp_path)
    index = settings.data_dir / "index/manifest.json"
    index.parent.mkdir(parents=True)
    index.write_text("first", encoding="utf-8")
    before = fingerprint(settings)
    calls = []

    def inspect(*_):
        index.write_text("changed by isolated test", encoding="utf-8")
        return review()

    with client_for([body()], calls) as client:
        result = capture_run(client=client, settings=settings, cases_path=FIXTURE,
                             output=tmp_path / "run", reviewer=inspect)
    assert before != fingerprint(settings) and len(calls) == 1
    assert result["stop_reason"] == "knowledge_changed"


def test_invalid_or_missing_review_stops(tmp_path):
    calls = []
    with client_for([body()], calls) as client:
        result = capture_run(client=client, settings=profile(tmp_path), cases_path=FIXTURE,
                             output=tmp_path / "run", reviewer=lambda *_: None)
    assert result["stop_reason"] == "manual_review_missing_or_invalid" and len(calls) == 1


@pytest.mark.parametrize("value", [-1, True, 13])
def test_invalid_model_call_accounting_cannot_advance(tmp_path, value):
    calls = []
    response = body().replace('"model_calls": 2', '"model_calls": ' + json.dumps(value))
    with client_for([response], calls) as client:
        result = capture_run(client=client, settings=profile(tmp_path), cases_path=FIXTURE,
                             output=tmp_path / "run", reviewer=lambda *_: review())
    assert len(calls) == 1 and result["stop_reason"] == "capture_budget_violation"


def test_hidden_login_never_returns_or_persists_password_or_token_in_records(tmp_path):
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"access_token": "test-secret-token"})
    with httpx.Client(base_url="http://127.0.0.1:8000", transport=httpx.MockTransport(handler)) as client:
        login_hidden(client, profile(tmp_path), lambda _: "test-secret-password")
        assert client.headers["authorization"] == "Bearer test-secret-token"
    assert len(requests) == 1 and requests[0].url.path == "/api/auth/login"
    assert not list(tmp_path.rglob("*.json"))
