import json


def _events(body: str):
    for block in body.split("\n\n"):
        event = next((line[7:] for line in block.splitlines() if line.startswith("event: ")), None)
        data = next((line[6:] for line in block.splitlines() if line.startswith("data: ")), None)
        if event and data:
            yield event, json.loads(data)


def test_usage_event_and_log_share_request_id_without_prompt_text(client, auth_headers, pdf_bytes):
    client.post("/api/knowledge/documents", headers=auth_headers, files={"file": ("manual.pdf", pdf_bytes, "application/pdf")})
    response = client.post("/api/chat/stream", headers=auth_headers, json={"question": "What is the data retention period?"})
    events = list(_events(response.text))
    usage = next(data for event, data in events if event == "usage")
    request_id = response.headers["x-request-id"]
    assert usage["request_id"] == request_id
    assert usage["model_calls"] <= 2 and usage["cloud_calls"] == 0
    assert usage["prompt_tokens"] >= 0 and usage["completion_tokens"] >= 0
    assert usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"]
    assert "prompt" not in usage.get("cache_hits", {})
    assert not any("messages" in item or "system_prompt" in item for item in usage)
    logs = client.get("/api/logs", headers=auth_headers, params={"request_id": request_id}).json()["items"]
    usage_log = next(item for item in logs if item["module"] == "rag.usage")
    assert usage_log["details"]["total_tokens"] == usage["total_tokens"]
    assert "query_representation" not in [item["stage"] for event, item in events if event == "step"]


def test_model_failure_exposes_safe_reason_not_exception_content(client, auth_headers, pdf_bytes):
    class BrokenProvider:
        def complete(self, messages, *, tools=None):
            raise ConnectionError("connect refused; prompt=private-pdf-text")

    client.post("/api/knowledge/documents", headers=auth_headers, files={"file": ("manual.pdf", pdf_bytes, "application/pdf")})
    client.app.state.services.pipeline.graph_service.generator.provider = BrokenProvider()
    response = client.post("/api/chat/stream", headers=auth_headers, json={"question": "What is the data retention period?"})
    events = list(_events(response.text))
    error = next(data for event, data in events if event == "error")
    failed = next(data for event, data in events if event == "step" and data["status"] == "failed")
    assert error["code"] == "LOCAL_MODEL_UNAVAILABLE"
    assert "本地模型" in error["message"] and failed["error"] == error["message"]
    assert "private-pdf-text" not in response.text
