import { Check, ChevronDown, Circle, Search, X } from "lucide-react";
import type { AnalysisEvent, ExecutionEvent, ParentToolResult, RetrievalResult, StageEvent, UsageEvent } from "../types/api";
import { activities, nodeNames } from "../features/chat/activity";
import { EvidenceList } from "../features/chat/EvidenceList";

const eventNames:Record<string,string>={node:"流程节点",model_start:"模型开始调用",model_call:"模型调用",agent_decision:"检索决策",query_rewritten:"问题补全与拆分",runtime_guard:"程序执行边界",hybrid_search:"混合检索",parent_retrieval:"父级读取",budget:"预算闸门"};
const guardNames:Record<string,string>={timeout:"达到时间上限",budget_exceeded:"调用预算已用尽",verification_failed:"引文校验未通过",invalid_model_output:"模型输出格式未通过",context_budget_exceeded:"模型上下文容量不足",model_unavailable:"模型调用失败",index_not_ready:"知识库索引尚未就绪"};
function detailText(event:ExecutionEvent) {
  const details=event.details ?? {};
  if(event.event==="query_rewritten") return [event.source==="cache"?"缓存复用":"问题补全与拆分",event.action==="new_question"?"用户选择新问题":event.relation_source==="pending_state"?"自动继续补充":"",event.query].filter(Boolean).join(" · ");
  if(event.event==="runtime_guard") return guardNames[String(details.stop_reason)] ?? String(details.stop_reason ?? "执行边界");
  if(event.event==="node") return `${nodeNames[event.node] ?? event.node}${details.status ? ` · ${["start","started"].includes(String(details.status))?"开始":details.status==="completed"?"完成":String(details.status)}`:""}`;
  if(event.event==="agent_decision") {
    const calls=Array.isArray(details.tool_calls)?details.tool_calls as {name:string;args?:Record<string,unknown>}[]:[];
    return calls.map(call=>call.name==="search_child_chunks"?`搜索：${String(call.args?.query ?? "")}`:`读取章节：${String(call.args?.parent_id ?? "")}`).join("；") || "研究决策";
  }
  return event.query || event.parent_id || nodeNames[event.node] || event.node;
}
export function ProcessPanel({stages,executionEvents,usage,notice,analysis,retrieval=[],parentResults=[]}: {stages:StageEvent[];executionEvents:ExecutionEvent[];usage?:UsageEvent|null;notice?:string;analysis?:AnalysisEvent|null;retrieval?:RetrievalResult[];parentResults?:ParentToolResult[];embedded?:boolean}) {
  const rows=activities(executionEvents);
  const tools=rows.filter(row=>row.event.event.startsWith("tool"));
  const provenance=executionEvents.length===0?"":executionEvents.every(e=>e.replayed===true)?"执行后回放":executionEvents.every(e=>e.replayed===false)?"实时更新":"按事件记录";
  return <div className="process-panel" aria-label="问答执行过程">
    {notice && <p className="process-notice">{notice}</p>}
    {analysis && <div className="query-analysis"><strong>查询分析</strong><p>{analysis.is_clear?"问题已明确":"需要补充信息"}</p>{analysis.questions.length>0 && <ul>{analysis.questions.map((q,index)=><li key={index}>{q}</li>)}</ul>}</div>}
    {tools.length>0 && <div className="tool-activities" aria-label="工具活动">{tools.map(row=><div className="tool-activity" key={row.key}>
      {row.status==="completed"?<Check aria-label="已完成"/>:row.status==="failed"?<X aria-label="失败"/>:<Search aria-label="正在执行"/>}
      <span><strong>{row.title}</strong><small>{row.status==="completed"?"已完成":row.status==="failed"?"执行失败":"正在执行"}{row.event.duration_ms!=null?` · ${row.event.duration_ms} ms`:""}</small></span>
    </div>)}</div>}
    <details className="technical-details"><summary><Circle aria-hidden="true"/><span>技术详情{provenance?` · ${provenance}`:""}</span><ChevronDown aria-hidden="true" className="details-chevron"/></summary>
      {usage && <dl className="usage-strip" aria-label="本次模型用量"><div><dt>模型调用</dt><dd><strong>{usage.model_calls}{usage.model_call_limit!=null?` / ${usage.model_call_limit}`:""}</strong></dd></div><div><dt>输入 / 输出 Token</dt><dd>{usage.prompt_tokens} / {usage.completion_tokens}</dd></div><div><dt>总 Token</dt><dd>{usage.total_tokens} · {usage.usage_source==="provider"?"实际":usage.usage_source==="mixed"?"部分估算":"估算"}</dd></div><div><dt>缓存命中</dt><dd>{usage.cache_hit_count}</dd></div><div><dt>总耗时</dt><dd>{usage.duration_ms} ms</dd></div></dl>}
      <div className="execution-list">{executionEvents.filter(event=>!["tool_start","tool_call","model_start","model_call"].includes(event.event)).map((event,index)=><div className="execution-row" key={index}><strong>{[event.branch_id,event.decision_source==="model"?"模型":event.decision_source==="runtime_guard"?"程序边界":null,eventNames[event.event]??event.event].filter(Boolean).join(" · ")}</strong><span>{detailText(event)}</span></div>)}
      {rows.filter(row=>!row.event.event.startsWith("tool")).map(row=><div className="execution-row" key={row.key}><strong>{row.title} · {row.status==="running"?"模型开始调用":row.status==="failed"?"调用失败":"模型调用完成"}</strong><span>{row.event.duration_ms!=null?`${row.event.duration_ms} ms`:""}{row.status!=="running" && row.event.details?.input_tokens!=null?` · ${String(row.event.details.input_tokens)} 输入 / ${String(row.event.details.output_tokens ?? 0)} 输出 Token${row.event.details.usage_source==="provider"?"":"（估算）"}`:""}</span></div>)}
      {stages.map((stage,index)=><div className="execution-row stage-row" key={`stage-${index}`}><strong>{stage.stage}</strong><span>{stage.status==="completed"?"完成":stage.status==="started"?"开始":stage.error||"失败"}</span></div>)}
      {tools.map(row=><p className="technical-id" key={row.key}>{row.event.tool} · {String(row.event.details?.tool_run_id ?? row.event.tool_call_id ?? "未提供调用标识")}</p>)}
      </div>
    </details>
    <EvidenceList sources={[]} retrieval={retrieval} parentResults={parentResults}/>
  </div>;
}
