from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

from app.rag import graph
from tests.fakes.reference_model import ScriptedReferenceModel, basic_resolver


@tool
def search_child_chunks(query: str, limit: int = 7) -> str:
    """Search document evidence."""
    return 'Parent ID: p1\nFile Name: guide.pdf\nContent: voltage is 230 V.'


def test_single_question_uses_native_research_and_always_aggregates():
    factory = getattr(graph, 'create_agent_graph', None)
    assert callable(factory), 'The approved native reference graph has not replaced ModelAgentLoop'
    model = ScriptedReferenceModel(resolver=basic_resolver)
    engine = factory(model, [search_child_chunks])
    result = engine.invoke({'messages': [HumanMessage(content='What voltage?')]},
                           {'configurable': {'thread_id': 'single'}, 'recursion_limit': 50})
    assert result['messages'][-1].content == 'Final answer: 230 V.\nSources:\n- guide.pdf'
    assert len(model.calls) == 4  # rewrite, first research, answer, aggregate
    assert result['agent_answers'][0]['answer'].startswith('The voltage')
    assert result['agent_answers'][0]['contexts']
    aggregate_input = model.calls[-1]['messages'][-1].content
    assert 'Original user question: What voltage?' in aggregate_input
    assert 'Retrieved response 1:' in aggregate_input
    assert 'Parent ID:' not in aggregate_input


def test_no_tool_answer_is_collected_without_old_retrieval_or_citation_gate():
    factory = getattr(graph, 'create_agent_graph', None)
    assert callable(factory), 'Reference final-answer semantics are missing'
    def respond(messages, kwargs, index):
        from langchain_core.messages import AIMessage
        if 'document-grounded research assistant' in str(messages[0].content):
            return AIMessage(content='No sufficient information in these sources.')
        return basic_resolver(messages, kwargs, index)
    model = ScriptedReferenceModel(resolver=respond)
    result = factory(model, [search_child_chunks]).invoke(
        {'messages': [HumanMessage(content='Question')]},
        {'configurable': {'thread_id': 'no-tools'}, 'recursion_limit': 50})
    assert result['agent_answers'][0]['answer'] == 'No sufficient information in these sources.'
    assert len(model.calls) == 3
