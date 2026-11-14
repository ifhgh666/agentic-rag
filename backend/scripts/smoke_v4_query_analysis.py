"""Read-only local-model smoke check for Stage 3 query analysis.

Run from backend: python -m scripts.smoke_v4_query_analysis
This script does not open the index, change thread memory or call cloud services.
"""

from __future__ import annotations

import json
import sys

from app.config import Settings
from app.core.conversation import PreparedQuery
from app.core.model_provider import OllamaProvider
from app.core.query_analysis import QueryAnalyzer


def main() -> None:
    settings = Settings()
    if settings.llm_provider != "ollama":
        raise SystemExit("只允许已配置的本机 Ollama 模式运行此冒烟检查。")
    provider = OllamaProvider(settings)
    if settings.ollama_model not in provider.check_connection():
        raise SystemExit("本机 Ollama 尚无配置的模型。")
    analyzer = QueryAnalyzer(settings, provider)
    cases = [
        ("standalone", "PX-200 的过流保护阈值是多少？", []),
        ("reference", "它多久维护一次？", [
            {"role": "user", "content": "PX-200 的过流保护阈值是多少？"},
            {"role": "assistant", "content": "已讨论 PX-200。"},
        ]),
        ("two_questions", "PX-200 的过流保护阈值是多少，以及运行记录默认保留多久？", []),
        ("ambiguous", "它的阈值是多少？", []),
    ]
    failures = 0
    for case_id, question, history in cases:
        if len(sys.argv) > 1 and case_id != sys.argv[1]:
            continue
        prepared = PreparedQuery("", history, question, True)
        result = analyzer.analyze(question, prepared, thread_id=f"smoke-{case_id}")
        trace = result.model_trace or {}
        expected_count = 0 if case_id == "ambiguous" else 2 if case_id == "two_questions" else 1
        passed = (result.is_clear == (case_id != "ambiguous") and len(result.questions) == expected_count
                  and not result.failure_reason)
        if case_id == "reference":
            passed = passed and "PX-200" in " ".join(result.questions)
        failures += not passed
        print(json.dumps({
            "case_id": case_id,
            "passed": bool(passed),
            "is_clear": result.is_clear,
            "question_count": len(result.questions),
            "questions": result.questions,
            "failure_reason": result.failure_reason,
            "clarification": result.clarification or None,
            "input_tokens": trace.get("input_tokens"),
            "output_tokens": trace.get("output_tokens"),
            "duration_ms": trace.get("duration_ms"),
            "provider": trace.get("provider"),
            "model": trace.get("model"),
        }, ensure_ascii=True), flush=True)
    if failures:
        raise SystemExit(f"{failures} local query analysis cases failed")


if __name__ == "__main__":
    main()
