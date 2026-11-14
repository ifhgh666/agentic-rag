export type DocumentStatus = "processing" | "ready" | "failed";

export interface HealthResponse {
  status: string;
  service: string;
  index_ready: boolean;
}

export interface DocumentItem {
  document_id: string;
  filename: string;
  status: DocumentStatus;
  size_bytes: number;
  uploaded_at: string;
  processed_at?: string | null;
  parent_count: number;
  child_count: number;
  error_reason?: string | null;
}

export interface SourceRef {
  document_id: string;
  filename: string;
  section_title: string;
  page_start?: number | null;
  page_end?: number | null;
}

export interface RetrievalResult {
  child_id: string;
  parent_id: string;
  document_id: string;
  filename: string;
  section_title: string;
  score: number;
  content_preview: string;
  text?: string;
  page_start?: number | null;
  page_end?: number | null;
}

export interface ParentToolResult {
  request_id: string;
  thread_id: string;
  tool: "retrieve_parent_chunks";
  tool_call_id: string;
  parent: SourceRef & { parent_id: string; text: string };
}

export interface StageEvent {
  request_id: string;
  thread_id?: string;
  stage: string;
  status: "started" | "completed" | "failed";
  sequence: number;
  duration_ms?: number | null;
  detail?: Record<string, unknown>;
  error?: string;
}

export type ChatAction = "auto" | "continue_clarification" | "new_question" | "cancel";

export interface QueryRewriteMetadata {
  loop_protocol_version?: string;
  source?: "model" | "cache" | "safe_fallback";
  relation_source?: "action" | "pending_state";
  action?: ChatAction;
  budget_node?: "query_analysis";
  model_call_id?: string | null;
  replayed?: boolean;
}

export interface AnalysisEvent extends QueryRewriteMetadata {
  schema_version: 1;
  request_id: string;
  thread_id: string;
  is_clear: boolean;
  relation: "new_question" | "clarification" | "uncertain";
  questions: string[];
  source: "model" | "cache" | "safe_fallback";
  duration_ms?: number | null;
}

export interface ClarificationEvent {
  loop_protocol_version?: string;
  replayed?: boolean;
  schema_version: 1;
  request_id: string;
  thread_id: string;
  pending: boolean;
  question: string;
  allowed_actions: Exclude<ChatAction, "auto">[];
}

export interface VerificationResult {
  schema_version: 2;
  request_id: string;
  thread_id: string;
  evidence_status: "found" | "insufficient" | "not_evaluated";
  citation_status: "verified" | "issue_found" | "not_applicable" | "not_evaluated";
  numeric_status: "verified" | "issue_found" | "not_applicable" | "not_evaluated";
  completeness_status: "verified" | "issue_found" | "not_evaluated";
  reason: string;
}

export interface ExecutionEvent extends QueryRewriteMetadata {
  loop_protocol_version?: string;
  branch_id?: string;
  decision_id?: string;
  tool_call_id?: string;
  event_sequence?: number;
  decision_source?: "model" | "cache" | "runtime_guard";
  request_id: string;
  thread_id: string;
  node: string;
  event: string;
  tool?: string | null;
  query?: string | null;
  parent_id?: string | null;
  duration_ms?: number | null;
  score?: number | null;
  iteration?: number | null;
  tool_call_count?: number | null;
  details?: Record<string, unknown>;
}

export interface UsageEvent {
  request_id?: string;
  thread_id?: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  usage_source: "provider" | "estimate" | "mixed";
  model_calls: number;
  model_call_limit: number | null;
  calls_by_node?: Record<string, number>;
  cache_hits?: Record<string, number>;
  cache_hit_count: number;
  model_duration_ms: number;
  duration_ms: number;
  budget_exceeded: boolean;
  cloud_calls: number;
}
