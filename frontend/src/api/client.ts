import axios from "axios";
import { clearToken, getToken } from "../auth/session";
import type {
  DocumentItem,
  EvaluationResult,
  LogItem,
  RetrievalResult,
  SourceRef,
  StageEvent,
  ExecutionEvent,
  UsageEvent,
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
    if (error.response?.status === 401) clearToken();
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
  await http.post("/auth/logout");
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

export async function listLogs(filters: { level?: string; module?: string; request_id?: string; thread_id?: string; limit?: number }): Promise<LogItem[]> {
  const response = await http.get<{ items: LogItem[] }>("/logs", { params: filters });
  return response.data.items;
}

export type StreamEvent =
  | { type: "step"; data: StageEvent }
  | { type: "query_rewritten"; data: ExecutionEvent & { query: string; is_clear: boolean } }
  | { type: "agent_decision"; data: ExecutionEvent & { action?: string } }
  | { type: "tool_call"; data: ExecutionEvent }
  | { type: "hybrid_search"; data: ExecutionEvent }
  | { type: "parent_retrieval"; data: ExecutionEvent }
  | { type: "budget"; data: ExecutionEvent }
  | { type: "node"; data: ExecutionEvent }
  | { type: "context_compression"; data: ExecutionEvent & { summary_chars?: number; removed_messages?: number; tokens_before?: number; tokens_after?: number; token_threshold?: number } }
  | { type: "model_call"; data: ExecutionEvent }
  | { type: "usage"; data: UsageEvent }
  | { type: "retrieval"; data: { request_id: string; thread_id: string; results: RetrievalResult[] } }
  | { type: "answer"; data: { request_id: string; thread_id: string; answer: string; sources: SourceRef[] } }
  | { type: "evaluation"; data: EvaluationResult }
  | { type: "error"; data: { request_id: string; thread_id: string; code: string; message: string } }
  | { type: "complete"; data: { request_id: string; thread_id: string; status: string; reason?: string | null } };

export async function streamChat(question: string, threadId: string | null, onEvent: (event: StreamEvent) => void): Promise<void> {
  const response = await fetch("/api/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${getToken() ?? ""}` },
    body: JSON.stringify({ question, ...(threadId ? { thread_id: threadId } : {}) }),
  });
  if (!response.ok || !response.body) {
    if (response.status === 401) clearToken();
    throw new Error("聊天请求无法建立。");
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
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
      onEvent({ type, data: JSON.parse(dataLine.replace("data:", "").trim()) } as StreamEvent);
    }
  }
}
