def test_list_documents(client, admin_headers):
    r = client.get("/api/documents", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 28
    assert len(data["documents"]) == data["total"]


def test_get_document_content(client, admin_headers):
    listed = client.get("/api/documents", headers=admin_headers).json()
    doc_id = listed["documents"][0]["id"]
    r = client.get(f"/api/documents/{doc_id}", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["content"]
    assert body["file_type"] in ("markdown", "pdf")
