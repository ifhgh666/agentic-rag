def test_logger_filters_by_request_id(tmp_path):
    from app.observability.logger import StructuredLogger

    logger = StructuredLogger(tmp_path / "app.jsonl")
    logger.log("INFO", "test", "one", "request-a")
    logger.log("ERROR", "test", "two", "request-b")
    assert len(logger.query(request_id="request-a")) == 1
    assert logger.query(level="ERROR")[0]["message"] == "two"


def test_logger_filters_by_thread_id_and_redacts_assignment_secrets(tmp_path):
    from app.observability.logger import StructuredLogger

    logger = StructuredLogger(tmp_path / "app.jsonl")
    logger.log("INFO", "test", "one", "request-a", thread_id="thread-a", details={"error": "api_key=secret-value"})
    logger.log("INFO", "test", "two", "request-b", thread_id="thread-b")
    assert len(logger.query(thread_id="thread-a")) == 1
    assert logger.query(thread_id="thread-a")[0]["details"]["error"] == "[已脱敏]"


def test_logger_writes_execution_fields_without_secrets(tmp_path):
    from app.observability.logger import StructuredLogger

    logger = StructuredLogger(tmp_path / "app.jsonl")
    logger.log(
        "INFO",
        "rag.execution",
        "工具完成",
        "request-a",
        thread_id="thread-a",
        node="tools",
        event="tool_call",
        tool="search_child_chunks",
        query="PN8733",
        iteration=1,
        tool_call_count=1,
        details={"api_key": "sk-secret", "count": 2},
    )
    item = logger.query(request_id="request-a")[0]
    assert item["thread_id"] == "thread-a"
    assert item["node"] == "tools"
    assert item["event"] == "tool_call"
    assert item["details"]["api_key"] == "[已脱敏]"
