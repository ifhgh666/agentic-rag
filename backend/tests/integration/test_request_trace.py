def test_request_id_is_shared_by_logs_and_stream(client, auth_headers, pdf_bytes):
    client.post("/api/knowledge/documents", headers=auth_headers, files={"file": ("guide.pdf", pdf_bytes, "application/pdf")})
    response = client.post("/api/chat/stream", headers=auth_headers, json={"question": "What is the data retention period?"})
    request_id = response.headers["x-request-id"]
    assert request_id in response.text
    logs = client.get("/api/logs", headers=auth_headers, params={"request_id": request_id}).json()["items"]
    assert logs and all(item["request_id"] == request_id for item in logs)
