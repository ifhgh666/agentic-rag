from concurrent.futures import ThreadPoolExecutor
from app.core.model_call import BoundedCache, ModelCallBudget, build_model_budget, summarize_usage
from app.core.conversation import ConversationMemory
from app.core.model_provider import ModelResult
from app.core.query_analysis import QueryAnalyzer
from app.core.legacy_rag import ModelQueryGenerator
from app.core.legacy_cache import RequestToolCache
from app.knowledge.retrieval import Retriever
from app.knowledge.stores import DocumentStore
from app.schemas.common import utc_now
from app.schemas.documents import DocumentStatus, KnowledgeDocument, SearchableChildUnit
from uuid import uuid4


def test_simple_and_complex_total_budgets_and_node_limits():
    budget = ModelCallBudget(simple_limit=2, complex_limit=4, node_limits={
        "query_analysis": 1, "query_rewrite": 1, "collect_answer": 1,
    })
    budget.start("simple")
    assert budget.reserve("simple", "query_analysis")
    assert budget.reserve("simple", "collect_answer")
    assert not budget.reserve("simple", "answer_repair")
    simple = budget.finish("simple")
    assert simple["model_calls"] == 2 and simple["budget_exceeded"]

    budget.start("complex")
    budget.set_complex("complex", True)
    with ThreadPoolExecutor(max_workers=5) as executor:
        allowed = list(executor.map(lambda _: budget.reserve("complex", "query_rewrite"), range(5)))
    assert sum(allowed) == 1
    assert budget.reserve("complex", "query_analysis")
    assert budget.reserve("complex", "answer_repair")
    assert budget.reserve("complex", "collect_answer")
    assert not budget.reserve("complex", "collect_answer")
    assert budget.finish("complex")["model_calls"] == 4


def test_bounded_cache_ttl_and_eviction(monkeypatch):
    now = [100.0]
    monkeypatch.setattr("app.core.model_call.time.monotonic", lambda: now[0])
    cache = BoundedCache(max_entries=2, ttl_seconds=10)
    cache.put(("v1", "q1"), [])
    assert cache.get(("v1", "q1")) == (True, [])
    cache.put(("v1", "q2"), 2)
    cache.put(("v1", "q3"), 3)
    assert cache.get(("v1", "q1"))[0] is False
    now[0] = 111.0
    assert cache.get(("v1", "q3"))[0] is False


def test_usage_prefers_provider_tokens_and_never_contains_prompt():
    summary = summarize_usage([
        {"node": "query_analysis", "provider": "ollama", "input_tokens": 25, "output_tokens": 9,
         "input_tokens_estimate": 28, "output_tokens_estimate": 11, "duration_ms": 7},
        {"node": "collect_answer", "provider": "ollama", "input_tokens": None, "output_tokens": None,
         "input_tokens_estimate": 60, "output_tokens_estimate": 20, "duration_ms": 13},
    ], {"model_calls": 2, "budget_exceeded": False, "limit": 2}, {"retrieval": 1}, 45)
    assert summary["prompt_tokens"] == 85
    assert summary["completion_tokens"] == 29
    assert summary["total_tokens"] == 114
    assert summary["usage_source"] == "mixed"
    assert summary["cache_hits"]["retrieval"] == 1
    assert summary["cloud_calls"] == 0
    assert "prompt" not in str(summary).lower().replace("prompt_tokens", "")


def test_query_analysis_cache_scoped_to_thread_and_index_version(settings):
    class Provider:
        def __init__(self):
            self.calls = 0

        def complete(self, messages, *, tools=None, response_schema=None):
            self.calls += 1
            return ModelResult(
                '{"is_clear":true,"questions":["PX-200 的阈值是多少？","PX-200 运行记录保存多久？"],"clarification_needed":""}',
                "ollama", "stub", 10, 10,
            )

    provider = Provider()
    version = ["index-v1"]
    request_cache = RequestToolCache()
    analyzer = QueryAnalyzer(
        settings, provider, cache=BoundedCache(), index_version=lambda: version[0], request_cache=request_cache,
    )
    analyzer.budget = build_model_budget(settings)
    for request_id in ("r1", "r2", "r3", "r4"):
        analyzer.budget.start(request_id)
    question = "PX-200 的阈值是多少，以及运行记录保存多久？"
    prepared = ConversationMemory().prepare("thread-1", question)
    first = analyzer.analyze(question, prepared, thread_id="thread-1", request_id="r1")
    second = analyzer.analyze(question, prepared, thread_id="thread-1", request_id="r2")
    assert first.is_clear and len(first.questions) == 2
    assert first.source == "model" and second.source == "cache"
    assert first.questions == second.questions and provider.calls == 1
    assert second.model_trace is None
    assert request_cache.stats("r2")["query_analysis"] == 1
    version[0] = "index-v2"
    analyzer.analyze(question, prepared, thread_id="thread-1", request_id="r3")
    analyzer.analyze(question, prepared, thread_id="thread-2", request_id="r4")
    assert provider.calls == 3


def test_retrieval_cache_invalidates_when_index_version_changes(settings):
    store = DocumentStore(settings.data_dir)
    document_id, parent_id = uuid4(), uuid4()
    store.save_document(KnowledgeDocument(
        document_id=document_id, filename="manual.pdf", status=DocumentStatus.ready,
        size_bytes=1, uploaded_at=utc_now(),
    ))
    child = SearchableChildUnit(
        child_id=uuid4(), parent_id=parent_id, document_id=document_id,
        text="PX-200 的阈值为 16 A。", char_count=21, ordinal=0,
    )

    class Index:
        version = "index-v1"
        retrieval_mode = "hybrid"
        calls = 0

        def search(self, query, top_k, min_score):
            self.calls += 1
            return [(0.9, child)]

    index = Index()
    retriever = Retriever(settings, index, store)
    assert retriever.search_with_cache("PX-200 阈值")[1] is False
    assert retriever.search_with_cache("PX-200 阈值")[1] is True
    assert index.calls == 1
    index.version = "index-v2"
    assert retriever.search_with_cache("PX-200 阈值")[1] is False
    assert index.calls == 2


def test_query_rewrite_cache_reuses_only_same_thread_and_version(settings):
    class Provider:
        calls = 0

        def complete(self, messages, *, tools=None):
            self.calls += 1
            return ModelResult("PX-200 过流保护阈值参数", "ollama", "stub", 10, 4)

    provider = Provider()
    version = ["v1"]
    hits = RequestToolCache()
    generator = ModelQueryGenerator(
        settings, provider, cache=BoundedCache(), index_version=lambda: version[0], request_cache=hits,
    )
    generator.budget = build_model_budget(settings)
    for request_id in ("r1", "r2", "r3"):
        generator.budget.start(request_id)
    first = generator.generate_with_result("PX-200 阈值", ["PX-200 阈值"], thread_id="t", request_id="r1")
    second = generator.generate_with_result("PX-200 阈值", ["PX-200 阈值"], thread_id="t", request_id="r2")
    assert first[0] == second[0]
    assert first[1] and second[1] is None
    assert provider.calls == 1 and hits.stats("r2")["query_rewrite"] == 1
    version[0] = "v2"
    generator.generate_with_result("PX-200 阈值", ["PX-200 阈值"], thread_id="t", request_id="r3")
    assert provider.calls == 2
