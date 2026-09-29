def test_question_answering_returns_answer_sources_and_evaluation(client, auth_headers, pdf_bytes):
    client.post("/api/knowledge/documents", headers=auth_headers, files={"file": ("guide.pdf", pdf_bytes, "application/pdf")})
    response = client.post("/api/chat/stream", headers=auth_headers, json={"question": "What is the data retention period?"})
    assert "event: answer" in response.text
    assert "guide.pdf" in response.text
    assert "event: evaluation" in response.text


def test_question_without_ready_document_is_explicit(client, auth_headers):
    response = client.post("/api/chat/stream", headers=auth_headers, json={"question": "不存在的问题"})
    assert "没有足够信息" in response.text
