"""Synthetic local Ollama clarification decisions; never opens the knowledge index."""

import json

from app.config import Settings
from app.core.conversation import PreparedQuery
from app.core.model_provider import OllamaProvider
from app.core.query_analysis import QueryAnalyzer


def main():
    settings = Settings()
    if settings.llm_provider != "ollama":
        raise SystemExit("Only local Ollama is supported.")
    provider = OllamaProvider(settings)
    provider.check_connection()
    analyzer = QueryAnalyzer(settings, provider)
    cases = [
        ("supplement_1", "PX-200", "auto", "clarification", True),
        ("supplement_2", "设备型号是 PX-200", "continue_clarification", "clarification", True),
        ("new_1", "运行记录默认保留多久？", "auto", "new_question", True),
        ("new_2", "设备多久进行一次例行维护？", "new_question", "new_question", True),
        ("uncertain_1", "都可以", "auto", "uncertain", False),
        ("uncertain_2", "就那样吧", "auto", "uncertain", False),
    ]
    failures = 0
    for case_id, question, action, relation, clear in cases:
        pending = "过流保护后如何恢复？" if action != "new_question" else ""
        prepared = PreparedQuery("", [], question, True, pending_query=pending, action=action)
        result = analyzer.analyze(question, prepared, thread_id=case_id)
        trace = result.model_trace or {}
        passed = result.is_clear == clear and result.relation == relation and not result.failure_reason
        if relation == "clarification" and clear:
            passed = passed and any("PX-200" in item and "恢复" in item for item in result.questions)
        failures += not passed
        print(json.dumps({
            "case_id": case_id, "passed": bool(passed), "is_clear": result.is_clear,
            "relation": result.relation, "questions": result.questions,
            "source": result.source, "decision_guard": trace.get("decision_guard"),
            "failure_reason": result.failure_reason, "clarification": result.clarification,
            "input_tokens": trace.get("input_tokens"), "output_tokens": trace.get("output_tokens"),
            "duration_ms": trace.get("duration_ms"),
        }, ensure_ascii=True), flush=True)
    if failures:
        raise SystemExit(f"{failures} local clarification cases failed")


if __name__ == "__main__":
    main()
