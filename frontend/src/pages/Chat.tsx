import { FormEvent, useState } from "react";
import { messageFromError, streamChat, type StreamEvent } from "../api/client";
import type { EvaluationResult, ExecutionEvent, RetrievalResult, SourceRef, StageEvent, UsageEvent } from "../types/api";
import { ProcessPanel } from "../components/ProcessPanel";
import { ScoreCard } from "../components/ScoreCard";

export function Chat() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<SourceRef[]>([]);
  const [stages, setStages] = useState<StageEvent[]>([]);
  const [retrieval, setRetrieval] = useState<RetrievalResult[]>([]);
  const [executionEvents, setExecutionEvents] = useState<ExecutionEvent[]>([]);
  const [evaluation, setEvaluation] = useState<EvaluationResult | null>(null);
  const [requestId, setRequestId] = useState("");
  const [threadId, setThreadId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [usage, setUsage] = useState<UsageEvent | null>(null);

  function newSession() {
    if (running) return;
    setThreadId(null); setQuestion(""); setAnswer(""); setSources([]); setStages([]); setRetrieval([]); setExecutionEvents([]); setEvaluation(null); setRequestId(""); setError(""); setNotice(""); setUsage(null);
  }

  async function ask(event: FormEvent) {
    event.preventDefault(); if (!question.trim() || running) return;
    setRunning(true); setAnswer(""); setSources([]); setStages([]); setRetrieval([]); setExecutionEvents([]); setEvaluation(null); setRequestId(""); setError(""); setNotice(""); setUsage(null);
    try {
      await streamChat(question.trim(), threadId, (streamEvent: StreamEvent) => {
        const eventThreadId = (streamEvent.data as { thread_id?: string }).thread_id;
        if (eventThreadId) setThreadId(eventThreadId);
        if (streamEvent.type === "step") { setStages((items) => [...items, streamEvent.data]); setRequestId(streamEvent.data.request_id); }
        if (["query_rewritten", "agent_decision", "tool_call", "hybrid_search", "parent_retrieval", "budget", "node", "context_compression", "model_call"].includes(streamEvent.type)) setExecutionEvents((items) => [...items, streamEvent.data as ExecutionEvent]);
        if (streamEvent.type === "usage") setUsage(streamEvent.data);
        if (streamEvent.type === "retrieval") { setRetrieval(streamEvent.data.results); setRequestId(streamEvent.data.request_id); }
        if (streamEvent.type === "answer") { setAnswer(streamEvent.data.answer); setSources(streamEvent.data.sources); setRequestId(streamEvent.data.request_id); }
        if (streamEvent.type === "evaluation") { setEvaluation(streamEvent.data); setRequestId(streamEvent.data.request_id); }
        if (streamEvent.type === "error") setError(streamEvent.data.message);
        if (streamEvent.type === "complete" && streamEvent.data.reason) setNotice(streamEvent.data.reason);
      });
    } catch (caught) { setError(messageFromError(caught)); } finally { setRunning(false); }
  }

  return <div className="page-wrap chat-page"><header className="page-header"><div><span className="eyebrow">ASK / 01</span><h2>问答台</h2><p>问题进入这里，证据从你的文档里回来。</p></div><div className="header-note"><span className="status-dot"><i />本地知识模式</span><span>{threadId ? "同一线程 · 可继续追问" : "新会话 · 等待提问"}</span><button className="secondary-button new-session-button" type="button" onClick={newSession} disabled={running}>新会话</button></div></header><section className="question-card panel"><div className="question-mark">?</div><form onSubmit={ask}><label htmlFor="question">你想知道什么？</label><textarea id="question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="例如：这份制度里，数据保留期限是多久？" maxLength={2000} disabled={running} /><div className="question-foot"><span>{question.length} / 2000</span><button className="primary-button" disabled={running || !question.trim()}>{running ? "正在穿过知识库…" : "开始检索"}<span>↗</span></button></div></form></section>{error && <div className="inline-error">{error}</div>}{(running || stages.length > 0 || executionEvents.length > 0 || usage) && <ProcessPanel stages={stages} retrieval={retrieval} executionEvents={executionEvents} usage={usage} notice={notice} />}{answer && <section className="answer-card panel"><div className="panel-heading"><div><span className="eyebrow">ANSWER / EVIDENCE</span><h3>回答</h3></div>{requestId && <span className="mono">{requestId.slice(0, 12)}…</span>}</div><div className="answer-text">{answer}</div>{sources.length > 0 && <div className="source-strip"><div className="subheading">来源</div>{sources.map((source) => <div className="source-chip" key={`${source.document_id}-${source.section_title}`}><span>↳</span><div><strong>{source.filename}</strong><small>{source.section_title || "未命名章节"}{source.page_start ? ` · 第 ${source.page_start} 页` : ""}</small></div></div>)}</div>}</section>}{evaluation && <ScoreCard evaluation={evaluation} />}</div>;
}
