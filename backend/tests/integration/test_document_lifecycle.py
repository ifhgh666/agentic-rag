def test_document_delete_removes_retrieval_content(client, auth_headers, pdf_bytes):
    first = client.post("/api/knowledge/documents", headers=auth_headers, files={"file": ("first.pdf", pdf_bytes, "application/pdf")}).json()
    second = client.post("/api/knowledge/documents", headers=auth_headers, files={"file": ("second.pdf", pdf_bytes, "application/pdf")}).json()
    assert first["document_id"] != second["document_id"]
    assert client.delete(f"/api/knowledge/documents/{first['document_id']}", headers=auth_headers).status_code == 204
    results = client.post("/api/debug/retrieve", headers=auth_headers, json={"query": "data retention period"}).json()["results"]
    assert all(item["document_id"] != first["document_id"] for item in results)
