import { useEffect, useRef, useState } from "react";
import { deleteDocument, listDocuments, messageFromError, uploadDocument } from "../api/client";
import type { DocumentItem } from "../types/api";
import { StateView } from "../components/StateView";

function formatBytes(value: number) { return value > 1024 * 1024 ? `${(value / (1024 * 1024)).toFixed(1)} MB` : `${(value / 1024).toFixed(0)} KB`; }
function formatDate(value: string) { return new Date(value).toLocaleString("zh-CN", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }); }

export function Knowledge() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  async function refresh() { try { setError(""); setDocuments(await listDocuments()); } catch (caught) { setError(messageFromError(caught)); } finally { setLoading(false); } }
  useEffect(() => { void refresh(); }, []);
  useEffect(() => { const timer = window.setInterval(() => { if (documents.some((item) => item.status === "processing")) void refresh(); }, 1800); return () => window.clearInterval(timer); }, [documents]);

  async function onUpload(file?: File) { if (!file) return; if (!file.name.toLowerCase().endsWith(".pdf")) { setError("请选择 PDF 文件。"); return; } setBusy(true); setError(""); try { await uploadDocument(file); await refresh(); } catch (caught) { setError(messageFromError(caught)); } finally { setBusy(false); if (inputRef.current) inputRef.current.value = ""; } }
  async function onDelete(item: DocumentItem) { if (!window.confirm(`确定删除“${item.filename}”吗？这会移除它的全部检索内容。`)) return; setBusy(true); try { await deleteDocument(item.document_id); await refresh(); } catch (caught) { setError(messageFromError(caught)); } finally { setBusy(false); } }

  return <div className="page-wrap"><header className="page-header"><div><span className="eyebrow">LIBRARY / 02</span><h2>知识库</h2><p>文档是答案的土壤。保持它们清晰、健康、可追溯。</p></div><div className="header-stat"><strong>{documents.length.toString().padStart(2, "0")}</strong><span>份文档</span></div></header><section className="upload-zone panel"><div className="upload-copy"><span className="upload-glyph">＋</span><div><h3>投放一份新的知识</h3><p>只接受文本型 PDF · 处理完成后自动建立父子索引</p></div></div><input ref={inputRef} type="file" accept="application/pdf,.pdf" hidden onChange={(event) => void onUpload(event.target.files?.[0])} /><button className="secondary-button" onClick={() => inputRef.current?.click()} disabled={busy}>{busy ? "处理中…" : "选择 PDF"}<span>↗</span></button></section>{error && <div className="inline-error">{error}</div>}<section className="document-section"><div className="section-label"><span>全部文档</span><span>{documents.filter((item) => item.status === "ready").length} 份已就绪</span></div>{loading ? <StateView kind="loading" title="正在读取知识库" description="正在同步服务端文档状态。" /> : documents.length === 0 ? <StateView kind="empty" title="知识库还是空的" description="上传第一份 PDF，开始建立你的可追溯答案空间。" action={<button className="text-button" onClick={() => inputRef.current?.click()}>上传第一份文档 →</button>} /> : <div className="doc-table">{documents.map((item) => <div className="doc-row" key={item.document_id}><div className="doc-icon">PDF</div><div className="doc-main"><strong>{item.filename}</strong><span>{formatDate(item.uploaded_at)} · {formatBytes(item.size_bytes)}</span></div><div className={`doc-status ${item.status}`}><i />{item.status === "ready" ? "已就绪" : item.status === "processing" ? "处理中" : "处理失败"}</div><div className="doc-count"><strong>{item.parent_count}</strong><span>父级</span><strong>{item.child_count}</strong><span>子级</span></div>{item.status === "failed" && <div className="doc-error">{item.error_reason}</div>}<button className="icon-button" onClick={() => void onDelete(item)} disabled={busy} aria-label={`删除${item.filename}`}>×</button></div>)}</div>}</section></div>;
}
