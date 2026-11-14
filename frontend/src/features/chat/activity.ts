import type { ExecutionEvent } from "../../types/api";

export interface Activity { key:string; title:string; event:ExecutionEvent; status:"running"|"completed"|"failed"|"recorded"; }
export const nodeNames:Record<string,string>={select_tool:"判断是否需要查询知识库",answer_direct:"直接回答",summarize_history:"整理会话历史",rewrite_query:"问题补全与拆分",orchestrator:"研究决策",tools:"执行工具",should_compress_context:"检查研究上下文容量",compress_context:"压缩研究上下文",fallback_response:"研究边界收尾",collect_answer:"收集分支答案",aggregate_answers:"汇总最终答案",diagnostics:"诊断记录"};
export const toolNames:Record<string,string>={search_child_chunks:"查找相关资料",retrieve_parent_chunks:"阅读完整章节"};
export function activities(events:ExecutionEvent[]):Activity[] {
  const rows:Activity[]=[]; const identities=new Map<string,number>();
  for(const [index,event] of events.entries()) {
    if(!["tool_start","tool_call","model_start","model_call"].includes(event.event)) continue;
    const isTool=event.event.startsWith("tool"); const details=event.details ?? {};
    const keys=(isTool ? [details.tool_run_id,event.tool_call_id ?? details.tool_call_id] : [event.model_call_id ?? details.model_call_id])
      .filter((key):key is string=>typeof key==="string" && Boolean(key)).map(key=>`${isTool?"tool":"model"}:${event.request_id}:${key}`);
    const existing=keys.map(key=>identities.get(key)).find(value=>value!==undefined);
    const position=existing ?? rows.length;
    const previous=rows[position]; const isStart=event.event.endsWith("start");
    const merged={...previous?.event,...event,details:{...previous?.event.details,...details}};
    const status:Activity["status"]=details.error_type ? "failed" : isStart ? previous?.status ?? "running" : "completed";
    rows[position]={key:previous?.key ?? keys[0] ?? `event:${index}`,title:isTool ? toolNames[event.tool ?? ""] ?? "执行检索工具" : nodeNames[event.node] ?? "模型调用",event:merged,status};
    for(const key of keys) identities.set(key,position);
  }
  return rows;
}
