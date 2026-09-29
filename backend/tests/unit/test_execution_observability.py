from uuid import uuid4

from app.observability.execution import build_execution_event, sanitize_details


def test_execution_event_contains_trace_fields_and_redacts_sensitive_values():
    request_id = str(uuid4())
    event = build_execution_event(
        request_id=request_id,
        thread_id="thread-a",
        node="tools",
        event="tool_call",
        tool="search_child_chunks",
        query="PN8733 保护功能",
        iteration=2,
        tool_call_count=3,
        score=0.91,
        details={
            "count": 7,
            "api_key": "sk-secret",
            "authorization": "Bearer secret",
            "prompt": "private prompt",
            "reasoning": "private reasoning",
        },
    )

    assert event["request_id"] == request_id
    assert event["thread_id"] == "thread-a"
    assert event["node"] == "tools"
    assert event["tool"] == "search_child_chunks"
    assert event["iteration"] == 2
    assert event["tool_call_count"] == 3
    assert event["score"] == 0.91
    assert event["details"]["count"] == 7
    assert event["details"]["api_key"] == "[已脱敏]"
    assert event["details"]["authorization"] == "[已脱敏]"
    assert event["details"]["prompt"] == "[已隐藏]"
    assert event["details"]["reasoning"] == "[已隐藏]"


def test_sanitize_details_limits_nested_text():
    result = sanitize_details({"nested": {"content": "x" * 30}}, max_chars=10)
    assert result["nested"]["content"] == "xxxxxxxxxx…"


def test_sanitize_details_redacts_secret_like_values_inside_messages():
    result = sanitize_details({"error": "provider rejected sk-live-secret Bearer abc.def"})
    assert "sk-live-secret" not in result["error"]
    assert "Bearer abc.def" not in result["error"]
