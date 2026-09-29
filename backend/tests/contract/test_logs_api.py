def test_logs_can_filter_by_request_id(client, auth_headers, pdf_bytes):
    client.post("/api/knowledge/documents", headers=auth_headers, files={"file": ("guide.pdf", pdf_bytes, "application/pdf")})
    stream = client.post("/api/chat/stream", headers=auth_headers, json={"question": "What is the data retention period?"})
    request_id = stream.headers["x-request-id"]
    response = client.get("/api/logs", headers=auth_headers, params={"request_id": request_id})
    assert response.status_code == 200
    assert all(item["request_id"] == request_id for item in response.json()["items"])


def test_logs_reject_invalid_level(client, auth_headers):
    response = client.get("/api/logs", headers=auth_headers, params={"level": "NOPE"})
    assert response.status_code == 422


def test_logs_can_filter_by_thread_id(client, auth_headers):
    response = client.get("/api/logs", headers=auth_headers, params={"thread_id": "missing-thread"})
    assert response.status_code == 200
    assert response.json()["items"] == []
