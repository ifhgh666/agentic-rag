import axios from "axios";
import { clearToken, getToken } from "../auth/session";
import type {
  HealthResponse,
  DocumentItem,
  VerificationResult,
  RetrievalResult,
  SourceRef,
  StageEvent,
  ExecutionEvent,
  UsageEvent,
  ChatAction,
  AnalysisEvent,
  ClarificationEvent,
  ParentToolResult,
} from "../types/api";

const http = axios.create({ baseURL: "/api" });

http.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && error.config?.url !== "/health") clearToken();
    return Promise.reject(error);
  },
);

export function messageFromError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return error.response?.data?.detail || error.response?.data?.error?.message || "请求失败，请稍后重试。";
  }
  return error instanceof Error ? error.message : "请求失败，请稍后重试。";
}

export async function login(username: string, password: string) {
  const response = await http.post<{ access_token: string; user: { username: string } }>("/auth/login", { username, password });
  return response.data;
}

export async function logout() {
  const token=getToken();
  await http.post("/auth/logout",undefined,{headers:token ? {Authorization:`Bearer ${token}`} : undefined});
}

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const { data } = await http.get<HealthResponse>("/health", { signal, timeout: 10000 });
  if (data?.status !== "ok" || typeof data.service !== "string" || typeof data.index_ready !== "boolean") {
    throw new Error("服务健康响应无效。");
  }
  return data;
}

export async function listDocuments(): Promise<DocumentItem[]> {
  const response = await http.get<{ items: DocumentItem[] }>("/knowledge/documents");
  return response.data.items;
}

export async function uploadDocument(file: File): Promise<DocumentItem> {
  const form = new FormData();
  form.append("file", file);
  const response = await http.post<{ document_id: string; filename: string; status: DocumentItem["status"] }>("/knowledge/documents", form);
  return {
    document_id: response.data.document_id,
    filename: response.data.filename,
    status: response.data.status,
    size_bytes: file.size,
    uploaded_at: new Date().toISOString(),
    parent_count: 0,
    child_count: 0,
  };
}

export async function deleteDocument(id: string): Promise<void> {
  await http.delete(`/knowledge/documents/${id}`);
}

export async function retrieve(query: string): Promise<RetrievalResult[]> {
  const response = await http.post<{ results: RetrievalResult[] }>("/debug/retrieve", { query });
  return response.data.results;
}

export type StreamEvent =
  | { type: "step"; data: StageEvent }
  | { type: "analysis"; data: AnalysisEvent }
  | { type: "clarification"; data: ClarificationEvent }
  | { type: "query_rewritten"; data: ExecutionEvent & { query: string; is_clear: boolean } }
  | { type: "agent_decision"; data: ExecutionEvent & { action?: string } }
  | { type: "tool_call"; data: ExecutionEvent }
  | { type: "tool_start"; data: ExecutionEvent }
  | { type: "tool_result"; data: ParentToolResult }
  | { type: "runtime_guard"; data: ExecutionEvent }
  | { type: "hybrid_search"; data: ExecutionEvent }
  | { type: "parent_retrieval"; data: ExecutionEvent }
  | { type: "budget"; data: ExecutionEvent }
  | { type: "node"; data: ExecutionEvent }
  | { type: "model_start"; data: ExecutionEvent }
  | { type: "model_call"; data: ExecutionEvent }
  | { type: "usage"; data: UsageEvent }
  | { type: "retrieval"; data: { request_id: string; thread_id: string; results: RetrievalResult[] } }
  | { type: "answer"; data: { request_id: string; thread_id: string; answer: string; sources: SourceRef[] } }
  | { type: "verification"; data: VerificationResult }
  | { type: "error"; data: { request_id: string; thread_id: string; code: string; message: string } }
  | { type: "complete"; data: { request_id: string; thread_id: string; status: string; reason?: string | null } };

export async function streamChat(question: string, threadId: string | null, onEvent: (event: StreamEvent) => void, action: ChatAction = "auto", signal?: AbortSignal): Promise<void> {
  const response = await fetch("/api/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${getToken() ?? ""}` },
    body: JSON.stringify({ question, action, ...(threadId ? { thread_id: threadId } : {}) }),
    signal,
  });
  if (!response.ok || !response.body) {
    if (response.status === 401) clearToken();
    throw new Error("聊天请求无法建立。");
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try { while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) {
      const eventLine = chunk.split("\n").find((line) => line.startsWith("event:"));
      const dataLine = chunk.split("\n").find((line) => line.startsWith("data:"));
      if (!eventLine || !dataLine) continue;
      const type = eventLine.replace("event:", "").trim() as StreamEvent["type"];
      const data = JSON.parse(dataLine.replace("data:", "").trim());
      // 正常聊天不再提供在线核验；旧服务发来的核验和评分也不进入界面。
      if (["evaluation", "verification", "answer_evaluation"].includes(String(type))) continue;
      if (type === "analysis" && !isAnalysis(data)) continue;
      if (type === "tool_result" && !isParentToolResult(data)) continue;
      if (!signal?.aborted) onEvent({ type, data } as StreamEvent);
      if (type === "complete") return;
    }
  } } finally {
    // Aborting an already closed body can reject; preserve the original read/parse outcome.
    try { await reader.cancel(); } catch { /* Body is closed or aborted. */ }
    reader.releaseLock();
  }
}

export function isParentToolResult(value: unknown): value is ParentToolResult {
  if (!value || typeof value !== "object") return false;
  const data = value as Record<string, unknown>;
  if (data.tool !== "retrieve_parent_chunks" || typeof data.request_id !== "string"
    || typeof data.thread_id !== "string" || typeof data.tool_call_id !== "string"
    || !data.parent || typeof data.parent !== "object") return false;
  const parent = data.parent as Record<string, unknown>;
  return ["parent_id", "document_id", "filename", "section_title", "text"].every((key) => typeof parent[key] === "string")
    && ["page_start", "page_end"].every((key) => parent[key] == null || (typeof parent[key] === "number" && Number.isFinite(parent[key])));
}

export function isAnalysis(value: unknown): value is AnalysisEvent {
  if (!value || typeof value !== "object") return false;
  const data = value as Record<string, unknown>;
  const referenceProtocol = data.loop_protocol_version === "reference.v1";
  return data.schema_version === 1 && typeof data.request_id === "string" && typeof data.thread_id === "string"
    && typeof data.is_clear === "boolean" && Array.isArray(data.questions)
    && data.questions.every((question) => typeof question === "string" && (referenceProtocol || question.trim().length > 0))
    && (referenceProtocol || (data.is_clear ? data.questions.length >= 1 && data.questions.length <= 3 : data.questions.length === 0))
    && ["new_question", "clarification", "uncertain"].includes(String(data.relation))
    && ["model", "cache", "safe_fallback"].includes(String(data.source))
    && (data.relation_source === undefined || ["action", "pending_state"].includes(String(data.relation_source)))
    && (data.action === undefined || ["auto", "new_question", "continue_clarification", "cancel"].includes(String(data.action)))
    && (data.budget_node === undefined || data.budget_node === "query_analysis")
    && (data.model_call_id === undefined || data.model_call_id === null || typeof data.model_call_id === "string");
}

export function isVerification(value: unknown): value is VerificationResult {
  if (!value || typeof value !== "object") return false;
  const data = value as Record<string, unknown>;
  const statuses = ["verified", "issue_found", "not_applicable", "not_evaluated"];
  return data.schema_version === 2 && typeof data.reason === "string"
    && typeof data.request_id === "string" && typeof data.thread_id === "string"
    && ["found", "insufficient", "not_evaluated"].includes(String(data.evidence_status))
    && statuses.includes(String(data.citation_status)) && statuses.includes(String(data.numeric_status))
    && ["verified", "issue_found", "not_evaluated"].includes(String(data.completeness_status))
    && !["overall", "relevance", "faithfulness", "completeness"].some((field) => field in data);
}
