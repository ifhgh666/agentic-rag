def test_evaluation_is_in_stream(client, auth_headers, pdf_bytes):
    client.post("/api/knowledge/documents", headers=auth_headers, files={"file": ("guide.pdf", pdf_bytes, "application/pdf")})
    response = client.post("/api/chat/stream", headers=auth_headers, json={"question": "What are the administrator duties?"})
    assert '"overall"' in response.text and '"reason"' in response.text
