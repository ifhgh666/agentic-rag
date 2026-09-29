import type { ExecutionEvent, RetrievalResult, StageEvent, UsageEvent } from "../types/api";

const stageNames: Record<string, string> = {
  query_receipt: "接收问题",
  query_representation: "问题表示",
  child_retrieval: "子级检索",
  score_filtering: "分数过滤",
  parent_retrieval: "父级加载",
  context_building: "上下文构建",
  answer_generation: "答案生成",
  answer_evaluation: "答案评估",
  context_compression: "上下文压缩",
};

const executionNames: Record<string, string> = {
  query_rewritten: "查询分析",
  agent_decision: "检索决策",
  tool_call: "工具调用",
  hybrid_search: "混合检索",
  parent_retrieval: "父级读取",
  budget: "预算闸门",
  context_compression: "上下文压缩",
  model_call: "模型调用",
  node: "流程节点",
};

function detailText(event: ExecutionEvent): string {
  const details = event.details ?? {};
  if (event.event === "hybrid_search") {
    const score = event.score == null ? "" : ` · 最高分 ${event.score.toFixed(2)}`;
    return `${String(details.count ?? 0)} 条结果 · ${String(details.retrieval_mode ?? "hybrid")}${score}`;
  }
  if (event.event === "model_call") {
    const input = details.input_tokens ?? details.input_tokens_estimate ?? 0;
    const output = details.output_tokens ?? details.output_tokens_estimate ?? 0;
    return `${String(input)} 输入 / ${String(output)} 输出 Token${details.usage_source === "provider" ? "" : "（估算）"}`;
  }
  if (event.event === "context_compression") return `${String(details.tokens_before ?? 0)} → ${String(details.tokens_after ?? 0)} Token`;
  if (event.event === "budget") return String(details.reason ?? "已达到调用预算");
  if (event.parent_id) return `Parent ${event.parent_id.slice(0, 8)}`;
  if (event.tool) return event.tool;
  if (event.query) return event.query.slice(0, 70);
  return event.node;
}

export function ProcessPanel({ stages, retrieval, executionEvents, usage, notice }: { stages: StageEvent[]; retrieval: RetrievalResult[]; executionEvents: ExecutionEvent[]; usage?: UsageEvent | null; notice?: string }) {
  const ordered = [...stages].sort((a, b) => a.sequence - b.sequence).filter((stage, index, all) => all.findIndex((item) => item.stage === stage.stage && item.status === stage.status) === index);
  return (
    <section className="process-panel panel" aria-label="问答执行过程">
      <div className="panel-heading"><div><span className="eyebrow">TRACE / 01</span><h3>一次执行的脉搏</h3></div><span className="mono">{stages.length ? `${stages.length} 个阶段事件` : "等待执行"}</span></div>
      {notice && <div className="process-notice" role="status"><span>!</span>{notice}</div>}
      {usage && <div className="usage-strip" aria-label="本次模型用量">
        <div><small>模型调用</small><strong>{usage.model_calls} / {usage.model_call_limit}</strong></div>
        <div><small>输入 / 输出</small><strong>{usage.prompt_tokens} / {usage.completion_tokens}</strong></div>
        <div><small>总 Token</small><strong>{usage.total_tokens}<em>{usage.usage_source === "provider" ? "实际" : usage.usage_source === "mixed" ? "部分估算" : "估算"}</em></strong></div>
        <div><small>缓存命中</small><strong>{usage.cache_hit_count}</strong></div>
        <div><small>总耗时</small><strong>{usage.duration_ms} ms</strong></div>
      </div>}
      <div className="stage-list">
        {ordered.map((stage) => (
          <div className={`stage-row ${stage.status}`} key={`${stage.stage}-${stage.status}-${stage.sequence}`}>
            <span className="stage-index">{String(stage.sequence).padStart(2, "0")}</span>
            <span className={`stage-symbol ${stage.status}`}>{stage.status === "completed" ? "✓" : stage.status === "failed" ? "!" : "·"}</span>
            <span className="stage-name">{stageNames[stage.stage] ?? stage.stage}</span>
            <span className="stage-status">{stage.status === "started" ? "进行中" : stage.status === "completed" ? stage.duration_ms != null ? `${stage.duration_ms} ms` : "完成" : stage.error ?? "失败"}</span>
          </div>
        ))}
      </div>
      {executionEvents.length > 0 && <div className="execution-list"><div className="subheading">执行轨迹 · {executionEvents.length}</div>{executionEvents.map((event, index) => <div className="execution-row" key={`${event.event}-${event.iteration ?? index}-${index}`}><span className="execution-node">{event.node}</span><strong>{executionNames[event.event] ?? event.event}</strong><span>{detailText(event)}</span><b>{event.duration_ms != null ? `${event.duration_ms} ms` : event.iteration ? `第 ${event.iteration} 轮` : ""}</b></div>)}</div>}
      {retrieval.length > 0 && <div className="retrieval-list"><div className="subheading">保留的证据 · {retrieval.length}</div>{retrieval.map((item) => <div className="evidence-row" key={item.child_id}><div><strong>{item.filename}</strong><span>{item.section_title || "未命名章节"} · 父级 {item.parent_id.slice(0, 8)}</span><p>{item.content_preview}</p></div><b>{item.score.toFixed(2)}</b></div>)}</div>}
    </section>
  );
}
