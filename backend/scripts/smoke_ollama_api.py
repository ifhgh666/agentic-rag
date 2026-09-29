"""使用隔离的临时知识库验证真实 Ollama 问答和执行日志。"""

import json
import os
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory

import fitz
from fastapi.testclient import TestClient

from app.auth.security import hash_password
from app.config import Settings


def main() -> None:
    configured = Settings()
    if configured.llm_provider != "ollama":
        raise RuntimeError("仅允许在本地 Ollama 模式运行真机验收")
    with TemporaryDirectory(prefix="v3-2-ollama-api-") as temp_dir, ExitStack() as stack:
        root = Path(temp_dir)
        # app.main 导入时会创建默认应用；必须先把该实例也隔离，避免争用正式 Qdrant。
        os.environ["DATA_DIR"] = str(root / "import-data")
        os.environ["QDRANT_DB_PATH"] = str(root / "import-qdrant")
        from app.main import app as imported_app, create_app
        stack.callback(imported_app.state.services.index.vector_db.client.close)

        settings = configured.model_copy(update={
            "data_dir": root / "test-data",
            "qdrant_db_path": root / "test-qdrant",
            "embedding_backend": "deterministic",
            "sparse_offline_fallback": True,
            "admin_username": "smoke",
            "admin_password_hash": hash_password("temporary-local-test-only"),
            "jwt_secret": "v3-2-test-only-secret-" + "x" * 32,
            "retrieval_min_score": 0.0,
        })
        client = TestClient(create_app(settings))
        stack.callback(client.app.state.services.index.vector_db.client.close)
        login = client.post("/api/auth/login", json={"username": "smoke", "password": "temporary-local-test-only"})
        login.raise_for_status()
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        document = fitz.open()
        page = document.new_page()
        page.insert_text((72, 72), "PX-200 overcurrent protection threshold is 16 A.")
        pdf_bytes = document.tobytes()
        document.close()
        upload = client.post(
            "/api/knowledge/documents",
            headers=headers,
            files={"file": ("local-smoke.pdf", pdf_bytes, "application/pdf")},
        )
        upload.raise_for_status()

        response = client.post(
            "/api/chat/stream",
            headers=headers,
            json={"question": "What is the PX-200 overcurrent protection threshold?", "thread_id": "v3-2-local-smoke"},
        )
        response.raise_for_status()
        events = []
        for block in response.text.split("\n\n"):
            lines = block.splitlines()
            event = next((line[7:] for line in lines if line.startswith("event: ")), None)
            data = next((line[6:] for line in lines if line.startswith("data: ")), None)
            if event and data:
                events.append((event, json.loads(data)))
        answers = [data.get("answer", "") for event, data in events if event == "answer"]
        if not answers or "16" not in answers[-1]:
            raise AssertionError(f"端到端问答没有得到预期事实；事件：{[name for name, _ in events]}")
        if any("<think>" in answer.lower() or len(answer) > 300 for answer in answers):
            raise AssertionError("端到端问答出现长篇分析或思考标签")

        request_id = response.headers["x-request-id"]
        logs_response = client.get("/api/logs", headers=headers, params={"request_id": request_id})
        logs_response.raise_for_status()
        calls = [item for item in logs_response.json()["items"] if item.get("event") == "model_call"]
        if len(calls) != 1:
            raise AssertionError("日志没有记录恰好一次模型调用")
        call = calls[0]
        if call["node"] != "collect_answer" or call["details"].get("provider") != "ollama":
            raise AssertionError("模型调用节点或提供商不正确")
        if not call["details"].get("input_tokens") or not call["details"].get("input_tokens_estimate"):
            raise AssertionError("日志缺少输入 Token 实际用量或估算")
        print(json.dumps({"answer": answers[-1], "model_call": call["details"], "duration_ms": call["duration_ms"]}, ensure_ascii=True))


if __name__ == "__main__":
    main()
