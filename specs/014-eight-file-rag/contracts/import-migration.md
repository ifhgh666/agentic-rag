# Import Migration Map

旧模块无转发文件。保留类/函数名称和行为，按下表迁移导入；原源码模块内的算法均有 AST 保留核对。

| 原模块 | 新模块与符号 |
|---|---|
| `agent_loop` | `nodes`：`FAILURE_TEXT`, `ModelAgentLoop`, `_TOOL_EXECUTOR`, `parse_json`, `render_answer`, `validate_answer` |
| `context_admission` | `tools`：`ContextAdmission` |
| `context_builder` | `tools`：`ContextBuilder` |
| `context_compression` | `tools`：`_CJK_RE`, `_WORD_RE`, `dynamic_token_threshold`, `estimate_tokens` |
| `conversation_memory` | `graph_state`：`ConversationMemory`, `MemorySnapshot`, `PreparedQuery` |
| `conversation_summary` | `nodes`：`summarize_conversation` |
| `cost_control` | `tools`：`BoundedCache`, `ModelCallBudget`, `build_model_budget`, `summarize_usage` |
| `edges` | `edges`：`route_after_prepare` |
| `embeddings` | `tools`：`EmbeddingService` |
| `evaluator` | `nodes`：`AnswerEvaluator` |
| `evidence` | `nodes`：`EvidenceSelector`, `_CHINESE_NUMBERS`, `_CHINESE_VALUE_RE`, `_ENDINGS`, `_HEADING`, `_HTML_BREAK`, `_LIST`, `_MODEL_ID_RE`, `_SENTENCE_RE`, `_VALUE_RE`, `_focused_excerpt`, `_matching_section`, `_overlap`, `_semantic_similarity`, `_terms`, `_values`, `eligible_units`, `find_numeric_conflict`, `format_conflict_answer`, `format_evidence_records`, `normalized`, `read_saved_markdown`, `recover_paragraphs`, `source_from_record` |
| `generator` | `nodes`：`AnswerGenerator`, `BUDGET_FALLBACK_PREFIX`, `INSUFFICIENT_ANSWER` |
| `graph` | `graph`：`AgentGraphService`, `_COMPAT_UNSET`, `_build_model_subgraph`, `build_agent_subgraph`, `build_main_graph` |
| `graph_state` | `graph_state`：`AgentState`, `ConversationTurn`, `Evidence`, `GraphRunResult`, `MainState`, `ThreadState`, `merge_agent_results`, `new_agent_state`, `new_main_state` |
| `index_store` | `tools`：`CHUNKER_VERSION`, `INDEX_SCHEMA_VERSION`, `IndexStore`, `PARSER_VERSION`, `_children_digest`, `_digest` |
| `model_call` | `schemas`：`AttemptRecord`, `CallOutcome`, `CallRecord`, `CallSpec`；`tools`：`CallContext`, `ModelCallRunner`, `_CallGuard`, `_Rejected`, `input_limit`, `input_tokens`, `operation_context`, `owned_call_context` |
| `model_provider` | `schemas`：`ModelResult`, `PreparedAttempt`；`tools`：`BeforeAttempt`, `ChatProvider`, `FakeProvider`, `OllamaProvider`, `OpenAICompatibleProvider`, `_MODEL_EXECUTOR`, `complete_model`, `create_provider`, `langchain_messages`, `normalize_tool_calls`, `openai_messages`, `rejects_structured_format`, `schema_instruction`, `token_details`, `visible_content`, `with_schema_instruction` |
| `nodes` | `nodes`：`analysis_failure_node`, `cancel_node`, `clarification_node`, `evaluate_node`, `model_loop_node`, `persist_memory_node`, `prepare_query_node`, `reduce_results_node`, `run_agent_node` |
| `pipeline` | `graph`：`RagPipeline`, `_PUBLIC_MODEL_FIELDS`, `_public_failure` |
| `prompts` | `prompts`：`REWRITE_PROMPT_VERSION`, `get_aggregation_instruction`, `get_aggregation_prompt`, `get_answer_context_marker`, `get_answer_generation_prompt`, `get_answer_repair_prompt`, `get_answer_request_input`, `get_branch_question_input`, `get_branch_synthesis_marker`, `get_branch_synthesis_payload`, `get_capacity_feedback_prompt`, `get_conversation_summary_prompt`, `get_grounded_evidence_payload`, `get_grounded_request_input`, `get_loop_repair_prompt`, `get_loop_resource_prompt`, `get_orchestrator_prompt`, `get_query_analysis_input`, `get_retrieval_rewrite_input`, `get_retrieval_rewrite_prompt`, `get_rewrite_query_prompt`, `get_schema_instruction_prompt` |
| `query_analysis` | `nodes`：`QUERY_REWRITE_POLICY_VERSION`, `QueryAnalyzer`, `REFERENCE_FALLBACK_VERSION`, `_CONSTRAINTS`, `_MODEL_ID`, `_NUMBER`, `_REFERENCE_MARKERS`, `_literal_constraints_preserved`, `_unique_history_reference`；`schemas`：`AnalysisOutcome` |
| `query_planner` | `nodes`：`ModelQueryGenerator`, `QueryGenerator`, `RuleBasedQueryGenerator`；`tools`：`normalize_query` |
| `retriever` | `tools`：`Retriever` |
| `schemas` | `schemas`：`BranchAnswer`, `EvidenceClaim`, `GroundedAnswer`, `GroundedCitation`, `QueryAnalysis`, `_query_clarity_schema` |
| `sparse_embeddings` | `tools`：`SparseEmbeddingService` |
| `tools` | `schemas`：`RetrieveParentInput`, `SearchChildInput`；`tools`：`RequestToolCache`, `create_rag_tools` |
| `vector_db_manager` | `tools`：`VectorDbManager` |
