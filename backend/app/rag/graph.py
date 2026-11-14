from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import ToolNode
from functools import partial
from .graph_state import State, AgentState
from .nodes import aggregate_answers, answer_direct, collect_answer, compress_context, fallback_response, orchestrator, request_clarification, rewrite_query, select_tool, should_compress_context, summarize_history
from .edges import route_after_history, route_after_orchestrator_call, route_after_rewrite

def create_agent_graph(llm, tools_list):
    llm_with_tools = llm.bind_tools(tools_list)
    tool_node = ToolNode(tools_list)
    checkpointer = InMemorySaver()
    print('Compiling agent graph...')
    agent_builder = StateGraph(AgentState)
    agent_builder.add_node('orchestrator', partial(orchestrator, llm_with_tools=llm_with_tools))
    agent_builder.add_node('tools', tool_node)
    agent_builder.add_node('compress_context', partial(compress_context, llm=llm))
    agent_builder.add_node('fallback_response', partial(fallback_response, llm=llm))
    agent_builder.add_node('should_compress_context', should_compress_context)
    agent_builder.add_node('collect_answer', collect_answer)
    agent_builder.add_edge(START, 'orchestrator')
    agent_builder.add_conditional_edges('orchestrator', route_after_orchestrator_call, {'tools': 'tools', 'fallback_response': 'fallback_response', 'collect_answer': 'collect_answer'})
    agent_builder.add_edge('tools', 'should_compress_context')
    agent_builder.add_edge('compress_context', 'orchestrator')
    agent_builder.add_edge('fallback_response', 'collect_answer')
    agent_builder.add_edge('collect_answer', END)
    agent_subgraph = agent_builder.compile()
    graph_builder = StateGraph(State)
    graph_builder.add_node('select_tool', partial(select_tool, llm=llm))
    graph_builder.add_node('summarize_history', partial(summarize_history, llm=llm))
    graph_builder.add_node('answer_direct', partial(answer_direct, llm=llm))
    graph_builder.add_node('rewrite_query', partial(rewrite_query, llm=llm))
    graph_builder.add_node('request_clarification', request_clarification)
    graph_builder.add_node('agent', agent_subgraph)
    graph_builder.add_node('aggregate_answers', partial(aggregate_answers, llm=llm))
    graph_builder.add_edge(START, 'select_tool')
    graph_builder.add_edge('select_tool', 'summarize_history')
    graph_builder.add_conditional_edges('summarize_history', route_after_history)
    graph_builder.add_edge('answer_direct', END)
    graph_builder.add_conditional_edges('rewrite_query', route_after_rewrite)
    graph_builder.add_edge('request_clarification', 'rewrite_query')
    graph_builder.add_edge(['agent'], 'aggregate_answers')
    graph_builder.add_edge('aggregate_answers', END)
    agent_graph = graph_builder.compile(checkpointer=checkpointer, interrupt_before=['request_clarification'])
    print('Agent graph compiled successfully.')
    return agent_graph
