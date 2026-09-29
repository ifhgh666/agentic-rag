def test_chat_stream_has_typed_events(client, auth_headers, pdf_bytes):
    client.post("/api/knowledge/documents", headers=auth_headers, files={"file": ("guide.pdf", pdf_bytes, "application/pdf")})
    response = client.post("/api/chat/stream", headers=auth_headers, json={"question": "What is the data retention period?"})
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: answer" in response.text
    assert "event: evaluation" in response.text


def test_chat_stream_returns_and_reuses_thread_id(client, auth_headers, pdf_bytes):
    client.post("/api/knowledge/documents", headers=auth_headers, files={"file": ("guide.pdf", pdf_bytes, "application/pdf")})
    response = client.post(
        "/api/chat/stream",
        headers=auth_headers,
        json={"question": "What is the data retention period?", "thread_id": "chat-contract"},
    )
    assert response.status_code == 200
    assert '"thread_id": "chat-contract"' in response.text


def test_chat_stream_clarifies_contextual_question_without_history(client, auth_headers):
    response = client.post(
        "/api/chat/stream",
        headers=auth_headers,
        json={"question": "那它的保护功能呢？", "thread_id": "new-chat"},
    )
    assert response.status_code == 200
    assert '"action": "clarification"' in response.text
    assert "event: retrieval" not in response.text


def test_multi_question_stream_exposes_analysis_and_subquestions(client, auth_headers, pdf_bytes):
    class AnalysisProvider:
        def complete(self, messages, *, tools=None):
            return ModelResult(
                content=json.dumps({
                    "is_clear": True,
                    "questions": ["What is the data retention period?", "How often do administrators review the policy?"],
                    "clarification_needed": None,
                }),
                provider="fake", model="analysis-stub",
            )

    service = client.app.state.services.pipeline.graph_service
    service.query_analyzer.provider = AnalysisProvider()
    client.post("/api/knowledge/documents", headers=auth_headers, files={"file": ("guide.pdf", pdf_bytes, "application/pdf")})
    response = client.post(
        "/api/chat/stream", headers=auth_headers,
        json={"question": "What is the data retention period, and how often is the policy reviewed?", "thread_id": "multi-contract"},
    )
    events = []
    for block in response.text.split("\n\n"):
        lines = block.splitlines()
        event = next((line[7:] for line in lines if line.startswith("event: ")), None)
        data = next((line[6:] for line in lines if line.startswith("data: ")), None)
        if event and data:
            events.append((event, json.loads(data)))
    analyses = [data for event, data in events if event == "query_rewritten"]
    assert len(analyses) == 1
    assert len(analyses[0]["details"]["questions"]) == 2
    assert any(event == "model_call" and data["node"] == "query_analysis" for event, data in events)
    assert len({data["details"].get("subquestion") for event, data in events if event == "tool_call" and data.get("tool") == "search_child_chunks"}) == 2
    assert any(event == "answer" and "1." in data["answer"] and "2." in data["answer"] for event, data in events)
import json

from app.rag.model_provider import ModelResult

