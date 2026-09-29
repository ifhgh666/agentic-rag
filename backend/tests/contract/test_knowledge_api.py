def test_upload_list_and_delete_document(client, auth_headers, pdf_bytes):
    response = client.post("/api/knowledge/documents", headers=auth_headers, files={"file": ("guide.pdf", pdf_bytes, "application/pdf")})
    assert response.status_code == 202
    document_id = response.json()["document_id"]
    documents = client.get("/api/knowledge/documents", headers=auth_headers).json()["items"]
    assert documents[0]["status"] == "ready"
    assert documents[0]["parent_count"] > 0
    assert "source_path" not in documents[0]
    assert client.delete(f"/api/knowledge/documents/{document_id}", headers=auth_headers).status_code == 204


def test_upload_rejects_non_pdf(client, auth_headers):
    response = client.post("/api/knowledge/documents", headers=auth_headers, files={"file": ("notes.txt", b"hello", "text/plain")})
    assert response.status_code == 422

