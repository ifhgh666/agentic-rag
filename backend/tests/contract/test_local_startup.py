import uvicorn
from fastapi.testclient import TestClient

from app import main as application
from scripts import start_local


def test_local_entry_binds_loopback_and_enables_demo_login(settings, monkeypatch):
    app = application.create_app(settings)
    monkeypatch.setattr(application, "app", app)
    monkeypatch.setattr(start_local, "get_settings", lambda: settings)
    original_secret = settings.jwt_secret

    class LocalServer:
        def __init__(self, config):
            assert config.app is app
            assert config.host == "127.0.0.1"
            assert config.port == 8000
            self.started = False

        def run(self):
            with TestClient(app, base_url="http://127.0.0.1:8000") as client:
                assert client.get("/api/health").status_code == 200
                assert client.get("/api/health", headers={"host": "example.invalid"}).status_code == 400
                assert client.post("/api/auth/login", json={"username": "admin", "password": "secret"}).status_code == 401
                response = client.post("/api/auth/login", json={"username": "admin", "password": "123456"})
                assert response.status_code == 200
                headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
                assert client.get("/api/knowledge/documents", headers=headers).status_code == 200
                assert client.post("/api/auth/logout", headers=headers).status_code == 204
                assert client.get("/api/knowledge/documents", headers=headers).status_code == 401
            self.started = True

    monkeypatch.setattr(uvicorn, "Server", LocalServer)
    assert start_local.main() == 0
    assert settings.jwt_secret != original_secret


def test_local_entry_reports_missing_compatible_provider_settings(settings, monkeypatch, capsys):
    settings.llm_provider = "openai_compatible"
    monkeypatch.setattr(start_local, "get_settings", lambda: settings)
    assert start_local.main() == 1
    assert "LLM_BASE_URL, LLM_API_KEY, LLM_MODEL" in capsys.readouterr().err
