def test_pipeline_emits_all_stages(client, auth_headers, pdf_bytes):
    client.post("/api/knowledge/documents", headers=auth_headers, files={"file": ("a.pdf", pdf_bytes, "application/pdf")})
    response = client.post("/api/chat/stream", headers=auth_headers, json={"question": "What is the data retention period?"})
    assert response.status_code == 200
    for stage in ("query_receipt", "child_retrieval", "score_filtering", "parent_retrieval", "context_building", "answer_generation", "answer_evaluation"):
        assert stage in response.text
    assert "query_representation" not in response.text
    assert "event: usage" in response.text
    assert "event: complete" in response.text
