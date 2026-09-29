def test_api_does_not_expose_storage_paths(client, auth_headers, pdf_bytes):
    response = client.post("/api/knowledge/documents", headers=auth_headers, files={"file": ("guide.pdf", pdf_bytes, "application/pdf")})
    document_id = response.json()["document_id"]
    item = client.get("/api/knowledge/documents", headers=auth_headers).json()["items"][0]
    assert "source_path" not in item and "markdown_path" not in item
    assert document_id == item["document_id"]


def test_upload_rejects_oversized_file(client, auth_headers, settings):
    settings.max_upload_bytes = 10
    response = client.post("/api/knowledge/documents", headers=auth_headers, files={"file": ("large.pdf", b"x" * 11, "application/pdf")})
    assert response.status_code == 422
