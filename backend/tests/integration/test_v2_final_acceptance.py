def test_v2_final_stream_is_traceable_and_redacted(client, auth_headers, pdf_bytes):
    health = client.get("/api/health")
    assert health.status_code == 200
    client.post(
        "/api/knowledge/documents",
        headers=auth_headers,
        files={"file": ("guide.pdf", pdf_bytes, "application/pdf")},
    )

    response = client.post(
        "/api/chat/stream",
        headers=auth_headers,
        json={"question": "What is the data retention period?", "thread_id": "final-thread"},
    )

    assert response.status_code == 200
    assert "event: analysis" in response.text
    assert "event: node" in response.text
    assert "event: tool_call" in response.text
    assert "event: retrieval" in response.text
    assert "event: model_call" in response.text
    assert "event: answer" in response.text
    assert "event: verification" not in response.text
    assert "event: evaluation" not in response.text
    assert "event: complete" in response.text
    assert '"thread_id": "final-thread"' in response.text
    assert "api_key" not in response.text.lower()
    assert "authorization" not in response.text.lower()
    assert "reasoning" not in response.text.lower()
    assert '"prompt":' not in response.text.lower()
    assert '"system_prompt":' not in response.text.lower()

    request_id = response.headers["x-request-id"]
    logs = client.get(
        "/api/logs",
        headers=auth_headers,
        params={"request_id": request_id},
    ).json()["items"]
    assert any(item.get("event") == "tool_call" for item in logs)
    model_calls = [item for item in logs if item.get("event") == "model_call"]
    assert len(model_calls) == 4
    assert {item["node"] for item in model_calls} == {"rewrite_query", "orchestrator", "aggregate_answers"}
    assert all(item["details"]["model_call_id"] for item in model_calls)
    assert model_calls[0]["details"]["input_tokens"] > 0
    assert model_calls[0]["details"]["usage_source"] == "estimate"
    assert all(item["details"]["replayed"] is False for item in model_calls)
    assert '"model_call_limit": null' in response.text
    assert all(item.get("thread_id") == "final-thread" for item in logs if item.get("thread_id"))
