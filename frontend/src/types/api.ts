export type DocumentStatus = "processing" | "ready" | "failed";

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

export interface EvaluationResult {
  request_id: string;
  thread_id?: string;
  relevance: number;
  faithfulness: number;
  completeness: number;
  overall: number;
  reason: string;
}

export interface ExecutionEvent {
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
  model_call_limit: number;
  calls_by_node?: Record<string, number>;
  cache_hits?: Record<string, number>;
  cache_hit_count: number;
  model_duration_ms: number;
  duration_ms: number;
  budget_exceeded: boolean;
  cloud_calls: number;
}

export interface LogItem {
  timestamp: string;
  level: string;
  module: string;
  request_id?: string | null;
  thread_id?: string | null;
  message: string;
  duration_ms?: number | null;
  error?: { message?: string } | null;
}
