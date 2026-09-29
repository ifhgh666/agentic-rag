def test_retrieval_diagnostic_returns_ordered_results(client, auth_headers, pdf_bytes):
    client.post("/api/knowledge/documents", headers=auth_headers, files={"file": ("guide.pdf", pdf_bytes, "application/pdf")})
    response = client.post("/api/debug/retrieve", headers=auth_headers, json={"query": "data retention period"})
    assert response.status_code == 200
    results = response.json()["results"]
    assert results and all("score" in item and "parent_id" in item for item in results)
