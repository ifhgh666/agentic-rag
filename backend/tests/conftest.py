import os
import sys
from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# 测试使用独立的本地 Qdrant 目录，避免和正在运行的开发服务争用本地锁。
os.environ.setdefault("QDRANT_DB_PATH", "pytest-qdrant")

from app.auth.security import hash_password
from app.config import Settings
from app.main import create_app


@pytest.fixture
def settings(tmp_path):
    return Settings(
        data_dir=tmp_path,
        admin_username="admin",
        admin_password_hash=hash_password("secret"),
        jwt_secret="a" * 40,
        llm_base_url="",
        llm_api_key="",
        llm_model="",
        llm_provider="fake",
        embedding_backend="deterministic",
        sparse_offline_fallback=True,
        retrieval_min_score=0.05,
    )


@pytest.fixture
def client(settings):
    return TestClient(create_app(settings))


@pytest.fixture
def auth_headers(client):
    response = client.post("/api/auth/login", json={"username": "admin", "password": "secret"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def pdf_bytes():
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "The data retention period is three years. Administrators review the policy every year.\nChapter One Management")
    content = document.tobytes()
    document.close()
    return content
