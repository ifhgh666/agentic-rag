import hashlib
import json
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
import pytest

from app.rag.graph import create_agent_graph
from tests.fakes.reference_baseline import baseline_graph
from tests.fakes.reference_model import ScriptedReferenceModel, basic_resolver


def canonical_calls(model):
    return sorted(json.dumps({'messages': [
        {'type': message.type, 'name': message.name, 'content': message.content,
         'tool_calls': getattr(message, 'tool_calls', [])} for message in call['messages']],
        'kwargs': call['kwargs']}, ensure_ascii=False, sort_keys=True) for call in model.calls)


@pytest.mark.parametrize('scenario', ['single', 'three', 'over_total_budget', 'compression', 'limit', 'no_tools', 'history'])
def test_business_messages_calls_answers_and_contexts_match_fixed_upstream(scenario):
    def resolve(messages, kwargs, index):
        system = str(messages[0].content)
        if 'query rewriting specialist' in system and scenario in {'three', 'over_total_budget'}:
            return AIMessage(content='', tool_calls=[{'name': 'QueryAnalysis', 'id': 'analysis', 'args': {
                'is_clear': True, 'questions': ['voltage?', 'current?', 'duration?'], 'clarification_needed': ''}}])
        if 'document-grounded research assistant' in system:
            count = sum(isinstance(message, ToolMessage) for message in messages)
            if scenario == 'no_tools':
                return AIMessage(content='Specific evidence is missing.')
            if scenario == 'compression' and any('COMPRESSED CONTEXT FROM PRIOR RESEARCH' in str(m.content) for m in messages):
                return AIMessage(content='The voltage is 230 V.\nSources:\n- guide.pdf')
            if scenario == 'limit' or (scenario == 'over_total_budget' and count < 3):
                return AIMessage(content='', tool_calls=[{'name': 'search_child_chunks', 'id': f'search-{count}',
                    'args': {'query': 'voltage', 'limit': 1}}])
        if 'constrained evidence synthesizer' in system:
            return AIMessage(content='Limited evidence answer.\nSources:\n- guide.pdf')
        return basic_resolver(messages, kwargs, index)

    tool_calls = []
    @tool
    def search_child_chunks(query: str, limit: int = 7) -> str:
        """Search document evidence."""
        tool_calls.append(query)
        # Keep the fixture above the fixed 2,000-token reference threshold;
        # 1,800 repetitions are still below it with cl100k_base tokenization.
        return 'Parent ID: p1\nFile Name: guide.pdf\nContent: ' + ('evidence ' * 2400 if scenario == 'compression' else 'voltage is 230 V.')

    outcomes = []
    with baseline_graph() as original:
        for factory in [original, create_agent_graph]:
            model = ScriptedReferenceModel(resolver=resolve)
            engine = factory(model, [search_child_chunks])
            config = {'configurable': {'thread_id': scenario}, 'recursion_limit': 50}
            tool_calls.clear()
            results = []
            for index in range(3 if scenario == 'history' else 1):
                visits = [(len(namespace), tuple(sorted(update))) for namespace, update in engine.stream(
                    {'messages': [HumanMessage(content=f'Question {index}?')]}, config,
                    stream_mode='updates', subgraphs=True)]
                result = engine.get_state(config).values
                results.append({'final': result['messages'][-1].content,
                    'summary': result.get('conversation_summary'),
                    'answers': sorted(result['agent_answers'], key=lambda row: row['index']),
                    # Branch completion order is nondeterministic; node visits
                    # and their multiplicities must still match the reference.
                    'node_visits': sorted(visits)})
            outcomes.append((results, canonical_calls(model), list(tool_calls)))
    assert outcomes[0] == outcomes[1]
    count = len(outcomes[1][1])
    if scenario == 'over_total_budget':
        assert count == 14  # More than the retired twelve-call total cap.
    if scenario == 'limit':
        assert len(outcomes[1][2]) == 8 and count == 12
    if scenario == 'compression':
        assert any('research context compressor' in row for row in outcomes[1][1])


def test_frozen_reference_files_match_original_git_blob_ids():
    root = Path(__file__).resolve().parents[1] / 'fixtures/reference016'
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    for path, digest in manifest['files'].items():
        data = (root / 'upstream' / path).read_bytes()
        actual = hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest()
        assert actual == digest, path
