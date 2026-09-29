"""V3-5 local regression: four real-PDF questions plus gap, follow-up, multi-fact and conflict."""

import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from app.config import Settings
from app.knowledge.stores import DocumentStore
from app.rag.context_builder import ContextBuilder
from app.rag.evaluator import AnswerEvaluator
from app.rag.generator import AnswerGenerator, INSUFFICIENT_ANSWER
from app.rag.graph import AgentGraphService
from scripts.smoke_v3_3 import main as multi_and_followup
from scripts.smoke_v3_4_baseline import main as four_pdf_questions
from scripts.smoke_v3_4_conflict import main as conflicting_sources


class EmptyRetriever:
    index_store = type("ReadyIndex", (), {"ready": True})()

    def search(self, query, top_k=None, min_score=None):
        return []


def no_evidence() -> dict:
    with TemporaryDirectory(prefix="v3-5-no-evidence-") as temp_dir:
        settings = Settings().model_copy(update={"data_dir": Path(temp_dir)})
        store = DocumentStore(settings.data_dir)
        result = AgentGraphService(
            settings=settings, retriever=EmptyRetriever(),
            context_builder=ContextBuilder(settings, store), generator=AnswerGenerator(settings),
            evaluator=AnswerEvaluator(), document_store=store,
        ).run("PX-200 的电池容量是多少？", thread_id="v3-5-gap")
        if result.status != "fallback" or result.final_answer != INSUFFICIENT_ANSWER or result.sources:
            raise AssertionError("无证据问题未安全返回信息不足")
        if result.usage["model_calls"] > 2 or result.usage["cloud_calls"]:
            raise AssertionError("无证据问题违反模型调用预算或发生云端调用")
        return {"status": result.status, "answer": result.final_answer, "usage": result.usage}


def main() -> None:
    if Settings().llm_provider != "ollama":
        raise RuntimeError("V3-5 真机回归必须使用本地 Ollama")
    # Keep the regression output concise; each sub-suite still raises on failure.
    with redirect_stdout(StringIO()):
        baseline = four_pdf_questions()
        gap = no_evidence()
        related = multi_and_followup()
        conflict = conflicting_sources()
    passed = sum(item["passed"] for item in baseline["cases"]) + 4
    if passed != 8:
        raise AssertionError("V3-5 八个回归场景未全部通过")
    print(json.dumps({
        "suite": "v3-5", "passed": passed, "total": 8,
        "case_ids": [item["question"] for item in baseline["cases"]] + ["NO_EVIDENCE", "FOLLOW_UP", "MULTI_FACT", "CONFLICT"],
        "cloud_calls": sum(item["usage"]["cloud_calls"] for item in baseline["cases"])
        + gap["usage"]["cloud_calls"] + related["usage"]["cloud_calls"]
        + related["clarification_usage"]["cloud_calls"] + related["clarified_usage"]["cloud_calls"]
        + conflict["usage"]["cloud_calls"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
