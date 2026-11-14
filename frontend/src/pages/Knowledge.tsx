import { useCallback, useEffect, useMemo, useRef, useState, type DragEvent } from "react";
import { AlertCircle, Check, ChevronDown, FileText, Info, LoaderCircle, RefreshCw, Search, Trash2, Upload } from "lucide-react";
import { deleteDocument, listDocuments, messageFromError, uploadDocument } from "../api/client";
import type { DocumentItem, DocumentStatus } from "../types/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "../components/ui/alert-dialog";

const statusText: Record<DocumentStatus, string> = { processing: "处理中", ready: "已就绪", failed: "处理失败" };
function formatBytes(value: number) {
  if (value >= 1024 * 1024) return `${(value / (1024 * 1024)).toFixed(1)} MB`;
  return value >= 1024 ? `${(value / 1024).toFixed(0)} KB` : `${value} B`;
}
function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString("zh-CN", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function Knowledge() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<"all" | DocumentStatus>("all");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [busy, setBusy] = useState<"upload" | "delete" | null>(null);
  const [listError, setListError] = useState("");
  const [operationError, setOperationError] = useState("");
  const [notice, setNotice] = useState("");
  const [dragging, setDragging] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<DocumentItem | null>(null);
  const [deleteError, setDeleteError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const cancelRef = useRef<HTMLButtonElement>(null);
  const deleteTriggerRef = useRef<HTMLButtonElement | null>(null);
  const alive = useRef(false);
  const mutationLock = useRef(false);
  const refreshVersion = useRef(0);
  const refreshInFlight = useRef(false);
  const dragDepth = useRef(0);

  const refresh = useCallback(async (force = false) => {
    if (!alive.current || (refreshInFlight.current && !force)) return;
    const version = ++refreshVersion.current;
    refreshInFlight.current = true;
    setRefreshing(true);
    try {
      const items = await listDocuments();
      if (alive.current && version === refreshVersion.current) { setDocuments(items); setListError(""); }
    } catch (error) {
      if (alive.current && version === refreshVersion.current) setListError(messageFromError(error));
    } finally {
      if (alive.current && version === refreshVersion.current) { refreshInFlight.current = false; setLoading(false); setRefreshing(false); }
    }
  }, []);

  useEffect(() => {
    alive.current = true;
    void refresh();
    return () => { alive.current = false; refreshVersion.current += 1; refreshInFlight.current = false; };
  }, [refresh]);
  const hasProcessing = documents.some(item => item.status === "processing");
  useEffect(() => {
    if (!hasProcessing) return;
    const timer = window.setInterval(() => { void refresh(); }, 1800);
    return () => window.clearInterval(timer);
  }, [hasProcessing, refresh]);

  const filtered = useMemo(() => {
    const name = query.trim().toLocaleLowerCase();
    return documents.filter(item => item.filename.toLocaleLowerCase().includes(name) && (status === "all" || item.status === status));
  }, [documents, query, status]);

  async function uploadFiles(files: File[]) {
    if (!files.length || mutationLock.current) return;
    setNotice("");
    if (files.length !== 1) { setOperationError("每次只能上传一个 PDF 文件，请重新选择。"); return; }
    const file = files[0];
    if (!file.name.toLowerCase().endsWith(".pdf")) { setOperationError("请选择 PDF 文件。"); return; }
    mutationLock.current = true;
    setBusy("upload"); setOperationError("");
    try {
      const uploaded = await uploadDocument(file);
      if (!alive.current) return;
      setDocuments(current => [uploaded, ...current.filter(item => item.document_id !== uploaded.document_id)]);
      setNotice(`已接收“${uploaded.filename}”，文档状态会自动更新。`);
      await refresh(true);
    } catch (error) {
      if (alive.current) setOperationError(messageFromError(error));
    } finally {
      mutationLock.current = false;
      if (alive.current) setBusy(null);
    }
  }

  async function confirmDelete() {
    if (!deleteTarget || mutationLock.current) return;
    mutationLock.current = true;
    setBusy("delete"); setDeleteError("");
    const target = deleteTarget;
    try {
      await deleteDocument(target.document_id);
      if (!alive.current) return;
      setDocuments(current => current.filter(item => item.document_id !== target.document_id));
      setDeleteTarget(null); setNotice(`已删除“${target.filename}”。`);
      await refresh(true);
    } catch (error) {
      if (alive.current) setDeleteError(messageFromError(error));
    } finally {
      mutationLock.current = false;
      if (alive.current) setBusy(null);
    }
  }

  function onDrop(event: DragEvent<HTMLElement>) {
    event.preventDefault(); dragDepth.current = 0; setDragging(false);
    void uploadFiles(Array.from(event.dataTransfer.files));
  }
  function clearFilters() { setQuery(""); setStatus("all"); searchRef.current?.focus(); }

  return (
    <div className="knowledge-workspace">
      <header className="knowledge-header">
        <div><h1>知识库</h1><p>管理文档，让答案有据可查。</p></div>
        <Button className="knowledge-upload-button" type="button" onClick={() => inputRef.current?.click()} disabled={Boolean(busy)}>
          {busy === "upload" ? <LoaderCircle className="knowledge-spin" aria-hidden="true" /> : <Upload aria-hidden="true" />}{busy === "upload" ? "正在上传…" : "上传 PDF"}
        </Button>
      </header>
      <p className="knowledge-summary" aria-live="polite">{loading ? "正在读取文档…" : listError && !documents.length ? "文档数量暂不可用" : <>{documents.length} 份文档<span aria-hidden="true">|</span>{documents.filter(item => item.status === "ready").length} 份已就绪</>}</p>
      <input ref={inputRef} type="file" accept="application/pdf,.pdf" hidden aria-label="选择 PDF 文件" disabled={Boolean(busy)} onChange={event => {
        const files = Array.from(event.currentTarget.files ?? []); event.currentTarget.value = ""; void uploadFiles(files);
      }} />
      <section className={`knowledge-dropzone${dragging && !busy ? " is-dragging" : ""}`} aria-label="上传 PDF 文档" aria-busy={busy === "upload"}
        onDragEnter={event => { event.preventDefault(); dragDepth.current += 1; if (!mutationLock.current) setDragging(true); }}
        onDragOver={event => { event.preventDefault(); event.dataTransfer.dropEffect = mutationLock.current ? "none" : "copy"; }}
        onDragLeave={event => { event.preventDefault(); dragDepth.current = Math.max(0, dragDepth.current - 1); if (!dragDepth.current) setDragging(false); }} onDrop={onDrop}>
        <div className="knowledge-drop-icon"><Upload aria-hidden="true" /></div>
        <div className="knowledge-drop-copy"><h2>{busy === "upload" ? "正在上传文档" : dragging ? "松开以上传这个 PDF" : "拖入一个 PDF 文件，或点击上传"}</h2><p>支持文本型 PDF，暂不支持扫描件</p></div>
        <Button variant="outline" type="button" onClick={() => inputRef.current?.click()} disabled={Boolean(busy)}>选择文件</Button>
      </section>
      {operationError && <p className="knowledge-feedback is-error" role="alert"><AlertCircle aria-hidden="true" />{operationError}</p>}
      {notice && !operationError && <p className="knowledge-feedback" role="status"><Check aria-hidden="true" />{notice}</p>}
      <div className="knowledge-toolbar">
        <div className="knowledge-search"><Search aria-hidden="true" /><Input ref={searchRef} value={query} onChange={event => setQuery(event.target.value)} aria-label="按文档名称搜索" placeholder="搜索文档名称…" type="search" /></div>
        <div className="knowledge-status-select"><select value={status} onChange={event => setStatus(event.target.value as "all" | DocumentStatus)} aria-label="按文档状态筛选"><option value="all">全部状态</option><option value="ready">已就绪</option><option value="processing">处理中</option><option value="failed">处理失败</option></select><ChevronDown aria-hidden="true" /></div>
        <Button className="knowledge-refresh" variant="outline" type="button" aria-label="刷新文档列表" disabled={refreshing || Boolean(busy)} onClick={() => void refresh()}><RefreshCw className={refreshing ? "knowledge-spin" : undefined} aria-hidden="true" />刷新</Button>
      </div>
      {listError && <p className="knowledge-feedback is-error" role="alert"><AlertCircle aria-hidden="true" />{listError}</p>}
      <section className="knowledge-documents" aria-label="知识库文档" aria-busy={loading}>
        {loading ? <div className="knowledge-empty" role="status"><LoaderCircle className="knowledge-spin" aria-hidden="true" /><h2>正在读取知识库</h2><p>正在同步文档状态。</p></div>
          : !documents.length && listError ? <div className="knowledge-empty"><AlertCircle aria-hidden="true" /><h2>文档列表暂不可用</h2><p>请点击刷新重试。</p></div>
          : !documents.length ? <div className="knowledge-empty"><FileText aria-hidden="true" /><h2>知识库还是空的</h2><p>上传第一份 PDF，为问答添加资料。</p><Button variant="outline" type="button" disabled={Boolean(busy)} onClick={() => inputRef.current?.click()}>上传第一份文档</Button></div>
          : !filtered.length ? <div className="knowledge-empty"><Search aria-hidden="true" /><h2>没有匹配的文档</h2><p>试试其他名称或状态。</p><Button variant="outline" type="button" onClick={clearFilters}>清除筛选</Button></div>
          : <div className="knowledge-table-scroll" tabIndex={0} role="region" aria-label="文档列表，可横向滚动">
            <table className="knowledge-table"><caption className="sr-only">知识库文档名称、大小、上传时间、状态和父级/子级块数量</caption>
              <thead><tr><th scope="col">文档名称</th><th scope="col">文件大小</th><th scope="col">上传时间</th><th scope="col">状态</th><th scope="col">父级 / 子级</th><th scope="col"><span className="sr-only">操作</span></th></tr></thead>
              <tbody>{filtered.map(item => <tr key={item.document_id}>
                <td><div className="knowledge-document-name"><FileText aria-hidden="true" /><div><strong>{item.filename}</strong>{item.status === "failed" && item.error_reason && <p className="knowledge-document-error">{item.error_reason}</p>}</div></div></td>
                <td>{formatBytes(item.size_bytes)}</td><td><time dateTime={item.uploaded_at}>{formatDate(item.uploaded_at)}</time></td>
                <td><span className={`knowledge-badge is-${item.status}`}>{item.status === "processing" ? <LoaderCircle className="knowledge-spin" aria-hidden="true" /> : item.status === "failed" ? <AlertCircle aria-hidden="true" /> : <i aria-hidden="true" />}{statusText[item.status]}</span></td>
                <td className="knowledge-counts">{item.status === "processing" ? "—" : `${item.parent_count} / ${item.child_count}`}</td>
                <td><Button variant="ghost" size="icon" className="knowledge-delete" type="button" aria-label={`删除${item.filename}`} disabled={Boolean(busy)} onClick={event => { deleteTriggerRef.current = event.currentTarget; setDeleteError(""); setDeleteTarget(item); }}><Trash2 aria-hidden="true" /></Button></td>
              </tr>)}</tbody>
            </table>
          </div>}
      </section>
      {!loading && documents.length > 0 && <footer className="knowledge-footer"><span>显示 {filtered.length} / {documents.length} 份文档</span><span><Info aria-hidden="true" />处理完成后，文档可用于知识库检索。</span></footer>}
      <AlertDialog open={Boolean(deleteTarget)} onOpenChange={(open, details) => { if (mutationLock.current) { details.cancel(); return; } if (!open) { setDeleteTarget(null); setDeleteError(""); } }}>
        <AlertDialogContent className="knowledge-confirm" initialFocus={cancelRef} finalFocus={() => deleteTriggerRef.current?.isConnected ? deleteTriggerRef.current : searchRef.current}>
          <AlertDialogHeader><AlertDialogTitle>删除这份文档？</AlertDialogTitle><AlertDialogDescription>将删除“<strong>{deleteTarget?.filename}</strong>”及其全部检索内容，此操作无法撤销。</AlertDialogDescription></AlertDialogHeader>
          {deleteError && <p className="knowledge-feedback is-error" role="alert"><AlertCircle aria-hidden="true" />{deleteError}</p>}
          <AlertDialogFooter><AlertDialogCancel ref={cancelRef} disabled={busy === "delete"}>取消</AlertDialogCancel><AlertDialogAction variant="destructive" disabled={busy === "delete"} onClick={() => void confirmDelete()}>{busy === "delete" && <LoaderCircle className="knowledge-spin" aria-hidden="true" />}确认删除</AlertDialogAction></AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
