"""Guard the single canonical Agent and prompt implementation in app.rag."""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
from app.rag import nodes, prompts, schemas
from app.core import legacy_prompts, legacy_summary
from app.core import answering as generator, legacy_rag as query_planner
from app.core.reference_session import AgentGraphService


BACKEND = Path(__file__).resolve().parents[2]
RAG_PACKAGE = BACKEND / "app" / "rag"


def test_agent_core_excludes_infrastructure_implementations():
    infrastructure = {
        "ChatProvider", "OllamaProvider", "OpenAICompatibleProvider", "ModelCallRunner",
        "ModelCallBudget", "EmbeddingService", "SparseEmbeddingService", "VectorDbManager",
        "IndexStore", "Retriever", "ContextBuilder", "ConversationMemory", "PreparedQuery",
        "RagPipeline", "QueryAnalyzer", "AnswerGenerator", "AnswerEvaluator", "EvidenceSelector",
    }
    misplaced = {}
    for path in RAG_PACKAGE.glob("*.py"):
        classes = {node.name for node in ast.parse(path.read_text(encoding="utf-8")).body
                   if isinstance(node, ast.ClassDef)}
        if classes & infrastructure:
            misplaced[path.name] = sorted(classes & infrastructure)
    assert misplaced == {}


def test_support_implementations_have_explicit_single_owners():
    expected = {
        "core/model_provider.py": {"ChatProvider", "OllamaProvider", "OpenAICompatibleProvider"},
        "core/model_call.py": {"ModelCallRunner", "ModelCallBudget", "CallContext", "CallRecord"},
        "core/conversation.py": {"ConversationMemory", "ThreadState", "PreparedQuery"},
        "core/query_analysis.py": {"QueryAnalyzer", "AnalysisOutcome"},
        "core/answering.py": {"AnswerGenerator", "AnswerEvaluator"},
        "core/legacy_rag.py": {"EvidenceSelector", "QueryGenerator"},
        "core/pipeline.py": {"RagPipeline"},
        "knowledge/embeddings.py": {"EmbeddingService", "SparseEmbeddingService"},
        "knowledge/index.py": {"IndexStore", "VectorDbManager"},
        "knowledge/retrieval.py": {"Retriever", "ContextBuilder"},
    }
    locations = {}
    for path in (BACKEND / "app").rglob("*.py"):
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            if isinstance(node, ast.ClassDef):
                locations.setdefault(node.name, []).append(path.relative_to(BACKEND / "app").as_posix())
    for owner, names in expected.items():
        for name in names:
            assert locations.get(name) == [owner], (name, locations.get(name))


def test_agent_responsibilities_live_in_the_single_rag_package():
    expected = {
        "__init__.py",
        "edges.py",
        "graph.py",
        "graph_state.py",
        "nodes.py",
        "prompts.py",
        "schemas.py",
        "tools.py",
    }
    assert expected == {path.name for path in RAG_PACKAGE.rglob("*.py")}
    legacy_package = BACKEND / "app" / ("rag" + "_agent")
    assert not any(legacy_package.rglob("*.py"))
    assert not (RAG_PACKAGE / "prompt.py").exists()
    assert not (RAG_PACKAGE / "model_schema.py").exists()
    assert not hasattr(schemas, "QueryDecision")


def test_production_and_pipeline_use_the_rag_graph():
    assert AgentGraphService.__module__ == "app.core.reference_session"
    main_source = (BACKEND / "app" / "main.py").read_text(encoding="utf-8")
    assert "from .core.reference_session import AgentGraphService" in main_source


def test_rag_runtime_imports_form_an_acyclic_dependency_graph():
    files = {"app." + path.relative_to(BACKEND / "app").with_suffix("").as_posix().replace("/", "."): path
             for path in (BACKEND / "app").rglob("*.py")}
    dependencies = {name: set() for name in files}
    for name, path in files.items():
        package = name.rsplit(".", 1)[0]
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom):
                module = importlib.util.resolve_name("." * node.level + (node.module or ""), package) if node.level else node.module
                if module in files:
                    dependencies[name].add(module)
                for alias in node.names:
                    child = (module or "") + "." + alias.name
                    if child in files:
                        dependencies[name].add(child)
            elif isinstance(node, ast.Import):
                dependencies[name].update(alias.name for alias in node.names if alias.name in files)
    visited = set()

    def visit(name, trail):
        assert name not in trail, f"RAG import cycle: {' -> '.join([*trail, name])}"
        if name in visited:
            return
        for dependency in dependencies[name]:
            visit(dependency, [*trail, name])
        visited.add(name)

    for name in files:
        visit(name, [])


def test_reference_and_frozen_legacy_prompts_have_explicit_separate_consumers():
    assert nodes.get_orchestrator_prompt is prompts.get_orchestrator_prompt
    assert nodes.get_context_compression_prompt is prompts.get_context_compression_prompt
    assert nodes.get_aggregation_prompt is prompts.get_aggregation_prompt
    assert generator.get_aggregation_prompt is legacy_prompts.get_aggregation_prompt
    assert query_planner.get_retrieval_rewrite_prompt is legacy_prompts.get_retrieval_rewrite_prompt
    assert legacy_summary.get_conversation_summary_prompt is legacy_prompts.get_conversation_summary_prompt
    assert legacy_prompts.REWRITE_PROMPT_VERSION == "rewrite-prompt-v6-zh"
    assert "query rewriting specialist" in prompts.get_rewrite_query_prompt()
    assert "repair" not in {name for name in vars(nodes) if name.startswith("get_")}

def test_normal_graph_imports_no_legacy_decision_stack():
    for name in ("graph.py", "nodes.py", "edges.py", "tools.py"):
        tree = ast.parse((RAG_PACKAGE / name).read_text(encoding="utf-8"))
        imports = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        assert not any(any(part in module for part in ("legacy_", "model_call", "query_analysis", "answering", "conversation")) for module in imports)
