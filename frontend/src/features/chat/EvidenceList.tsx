import { ChevronDown, FileText } from "lucide-react";
import type { ParentToolResult, RetrievalResult, SourceRef } from "../../types/api";

const pages=(start?:number|null,end?:number|null)=>start==null ? end==null?"":`第 ${end} 页` : `第 ${start}${end!=null&&end!==start?`–${end}`:""} 页`;
export function EvidenceList({sources,retrieval,parentResults}:{sources:SourceRef[];retrieval:RetrievalResult[];parentResults:ParentToolResult[]}) {
  if(!sources.length && !retrieval.length && !parentResults.length) return null;
  return <div className="turn-evidence">
    {sources.length>0 && <div className="source-strip" aria-label="回答来源"><span className="evidence-label">来源</span>{sources.map((source,index)=><span className="source-chip" key={`${source.document_id}-${source.section_title}-${index}`}><FileText aria-hidden="true"/><strong>{source.filename}</strong><small>{[source.section_title,pages(source.page_start,source.page_end)].filter(Boolean).join(" · ")}</small></span>)}</div>}
    {(retrieval.length>0 || parentResults.length>0) && <details className="evidence-details"><summary><FileText aria-hidden="true"/><span>查看资料原文 · {retrieval.length+parentResults.length}</span><ChevronDown aria-hidden="true" className="details-chevron"/></summary><div className="retrieval-list">
      {retrieval.map(item=><details className="evidence-row" key={item.child_id}><summary><span><strong>{item.filename}</strong><small>{[item.section_title,pages(item.page_start,item.page_end)].filter(Boolean).join(" · ")}</small></span><span className="evidence-score">相关度 {item.score.toFixed(2)}</span></summary><p>{item.text || item.content_preview}</p><small className="technical-id">子块 {item.child_id} · 父级 {item.parent_id}</small></details>)}
      {parentResults.map(({parent,tool_call_id})=><details className="evidence-row" key={`${tool_call_id}-${parent.parent_id}`}><summary><span><strong>{parent.filename}</strong><small>{[parent.section_title,pages(parent.page_start,parent.page_end),"完整章节"].filter(Boolean).join(" · ")}</small></span></summary><p>{parent.text}</p><small className="technical-id">父级 {parent.parent_id} · 调用 {tool_call_id}</small></details>)}
    </div></details>}
  </div>;
}
