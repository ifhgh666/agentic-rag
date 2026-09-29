def test_protected_routes_require_authentication(client):
    assert client.get("/api/knowledge/documents").status_code == 401


def test_login_and_logout_revoke_token(client):
    bad = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert bad.status_code == 401
    login = client.post("/api/auth/login", json={"username": "admin", "password": "secret"})
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.post("/api/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/knowledge/documents", headers=headers).status_code == 401

