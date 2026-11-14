"""收尾的离线协议与已捕获证据回归，不冒充十五题正式模型验收。

协议场景使用脚本化分析器和已就绪的空检索；正文审计只读取版本化的真实
V3-8 捕获。没有网络模型、正式索引写入或自动人工审核。
"""

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.core.conversation import ConversationTurn
from app.core.model_provider import ModelResult
from scripts.smoke_v3_8 import captures_stable


ROOT = Path(__file__).resolve().parents[3]
FEATURE = ROOT / "specs/004-query-clarification-ragas"
V3 = ROOT / "specs/003-v3-ollama-rag-quality"
DATASET = json.loads((FEATURE / "gold-cases-v1.json").read_text(encoding="utf-8"))
CASES = DATASET["cases"]


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def normalized(text):
    return "".join(text.split())


def stream_events(response):
    assert response.status_code == 200
    return [(block.splitlines()[0].removeprefix("event: "),
             json.loads(next(line[6:] for line in block.splitlines() if line.startswith("data: "))))
            for block in response.text.split("\n\n") if block.strip()]


class ScriptedAnalysis:
    """仅驱动协议，返回的决定不代表真实模型的理解正确率。"""

    def __init__(self, decisions):
        self.decisions = list(decisions)
        self.calls = []

    def complete(self, messages, *, tools=None, response_schema=None):
        self.calls.append(messages)
        return ModelResult(json.dumps(self.decisions.pop(0), ensure_ascii=False), "fake", "protocol-stub", 20, 8)


def analysis(questions, relation="new_question"):
    return {"is_clear": bool(questions), "questions": questions,
            "clarification_needed": "" if questions else "请说明设备型号。"}


@pytest.mark.parametrize("case", CASES, ids=[case["case_id"] for case in CASES])
def test_all_candidate_scenarios_have_offline_sse_and_state_coverage(client, auth_headers, case, ready_empty_index):
    # This drives the reference protocol, never scores real model answers.
    from langchain_core.messages import AIMessage, HumanMessage
    from tests.fakes.reference_api import install_model, send, last
    from tests.fakes.reference_model import basic_resolver
    steps = case.get('flow_steps') if case['case_type'] == 'clarification_flow' else [
        {'question': case['question'], 'action': 'auto', 'expected_questions': [case['question']]}]
    decisions = [analysis(step['expected_questions']) for step in steps if step['action'] != 'cancel']
    def resolve(messages, kwargs, index):
        if 'query rewriting specialist' in str(messages[0].content):
            return AIMessage(content='', tool_calls=[{'name': 'QueryAnalysis', 'id': 'analysis', 'args': decisions.pop(0)}])
        return basic_resolver(messages, kwargs, index)
    graph, model, _ = install_model(client, resolve, text='Synthetic protocol-only evidence.')
    thread = 'candidate-' + case['case_id']
    history = case.get('history_fixture', [])
    if history:
        graph.main_graph.update_state(graph.config(thread), {'messages': [
            (HumanMessage if item['role'] == 'user' else AIMessage)(content=item['content']) for item in history]},
            as_node='aggregate_answers')
    request_ids = set()
    for step in steps:
        count = len(model.calls)
        stream = send(client, auth_headers, step['question'], thread=thread, action=step['action'])
        complete = last(stream, 'complete')
        expected = 'cancelled' if step['action'] == 'cancel' else 'completed' if step['expected_questions'] else 'clarification'
        assert complete['status'] == expected
        assert complete['thread_id'] == thread and complete['request_id'] not in request_ids
        request_ids.add(complete['request_id'])
        assert not {'verification', 'evaluation'}.intersection(name for name, _ in stream)
        usage = last(stream, 'usage')
        assert usage['model_call_limit'] is None and usage['cloud_calls'] == 0
        if step['action'] == 'cancel':
            assert len(model.calls) == count and not graph.get_state(thread).next
        else:
            assert last(stream, 'analysis')['questions'] == step['expected_questions']
            assert len(model.calls) > count
    assert not decisions


@pytest.mark.parametrize("case_id", [f"Q{i}" for i in range(1, 6)])
def test_captured_workbench_answers_keep_actual_text_sources_and_budget(case_id):
    observation = read_json(V3 / "v3-8-workbench-observation.json")
    case = next(row for row in observation["cases"] if row["case_id"] == case_id)
    assert observation["workbench_ui_run"] and observation["new_session_per_question"]
    assert hashlib.sha256(case["actual_answer"].encode("utf-8")).hexdigest() == observation["page_answer_sha256"][case_id]
    assert case["sources"] and case["first_tool"] == "search_child_chunks"
    assert case["usage"]["model_calls"] == 2 and case["usage"]["cloud_calls"] == 0
    assert case["usage"]["total_tokens"] == case["actual_input_tokens"] + case["usage"]["completion_tokens"]
    assert case["verification_display"]["引文定位"] == "已核验"
    assert case["verification_display"]["步骤完整性"] == "未评估"


def test_v3_8_dependency_keeps_three_distinct_same_version_q3_captures():
    observation = read_json(V3 / "v3-8-observation.json")
    assert observation["stage_complete"] and observation["workbench_validation"]["status"] == "passed"
    assert captures_stable(observation["cases"])
    q3 = next(case for case in CASES if case["case_id"] == "Q3")
    captures = [row for row in observation["cases"] if row["case_id"] == "Q3"]
    captures.append(next(row for row in read_json(V3 / "v3-8-workbench-observation.json")["cases"] if row["case_id"] == "Q3"))
    for capture in captures:
        body = normalized(capture.get("response", capture.get("actual_answer", "")).split("依据：", 1)[0])
        positions = [body.find(normalized(fact)) for fact in q3["ordered_facts"]]
        assert all(position >= 0 for position in positions)
        assert positions == sorted(set(positions))
        assert any(source.get("page", source.get("page_start")) == 3 for source in capture["sources"])
    # Compare historical captures to their own version, never require new feature
    # source files to retain the hash of the previous implementation.
    workbench = read_json(V3 / "v3-8-workbench-observation.json")
    protection = workbench["source_protection"]
    assert protection["reference"] == "v3-8-observation.json/protected_hashes"
    assert protection["same_version_as_isolated_captures"] and not protection["changed"]
    assert protection["protected_count"] == len(observation["protected_hashes"])


def test_v3_threshold_pass_is_not_silently_promoted_to_stricter_candidate_acceptance():
    q2 = next(case for case in CASES if case["case_id"] == "Q2")
    captured = next(row for row in read_json(V3 / "v3-8-workbench-observation.json")["cases"] if row["case_id"] == "Q2")
    assert "立即断开主回路" in q2["required_facts"]
    assert "立即断开主回路" not in normalized(captured["actual_answer"])
    # 这是候选验收口径的已知差异，不是声称当前答案已满足全部必答点。


def test_gold_review_has_explicit_provenance_and_keeps_scenario_coverage():
    assert len(CASES) >= 15
    assert len({case["category"] for case in CASES if case["case_id"] not in {f"Q{i}" for i in range(1, 6)}}) >= 10
    for case in CASES:
        if case["review_status"] == "draft":
            assert not case.get("reviewer") and not case.get("reviewed_at")
        else:
            assert case["review_status"] == "reviewed" and case["review_kind"] == "human"
            assert case["reviewer"] and case["reviewed_at"]
    if DATASET["status"] == "reviewed":
        assert all(case["review_status"] == "reviewed" for case in CASES)
