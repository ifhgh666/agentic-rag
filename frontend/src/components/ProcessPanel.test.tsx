import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ProcessPanel } from "./ProcessPanel";

describe("V3-5 过程面板", () => {
  it("子块和已读取Parent原文可展开，完整文本与真实页码保留且作为纯文本显示", () => {
    const childText = "子块开始\n" + "完整子块正文".repeat(60) + "子块末尾";
    const parentText = "父级开始\n" + "完整父级正文".repeat(100) + "<script>末尾原文</script>";
    const html = renderToStaticMarkup(<ProcessPanel stages={[]} executionEvents={[]}
      retrieval={[
        { child_id: "c1", parent_id: "p", document_id: "d", filename: "设备.pdf", section_title: "恢复", score: 0.9, content_preview: "短预览", text: childText, page_start: 4, page_end: 5 },
        { child_id: "c2", parent_id: "p2", document_id: "d", filename: "设备.pdf", section_title: "旧检索", score: 0.8, content_preview: "仅旧预览", text: "" },
      ]}
      parentResults={[{ request_id: "r", thread_id: "t", tool: "retrieve_parent_chunks", tool_call_id: "call-parent",
        parent: { parent_id: "p", document_id: "d", filename: "设备.pdf", section_title: "完整章节", page_start: 4, page_end: 7, text: parentText } }]} />);
    const view = document.createElement("div"); view.innerHTML = html;
    const details = [...view.querySelectorAll<HTMLDetailsElement>("details.evidence-row")];
    expect(details).toHaveLength(3);
    expect(details.every((item) => !item.open)).toBe(true);
    expect(details.map((item) => item.querySelector("p")?.textContent)).toEqual([childText, "仅旧预览", parentText]);
    expect(view.textContent).toContain("第 4–5 页");
    expect(view.textContent).toContain("第 4–7 页");
    expect(view.querySelector("script")).toBeNull();
    expect(view.textContent).not.toContain("已核验");
  });
  it("参考节点区分开始与完成，模型启动不伪造已完成用量", () => {
    const base = { request_id: "r", thread_id: "t", node: "compress_context", replayed: false, loop_protocol_version: "reference.v1" };
    const html = renderToStaticMarkup(<ProcessPanel stages={[]} retrieval={[]} executionEvents={[
      { ...base, event: "node", details: { status: "start" } },
      { ...base, event: "model_start", details: { model_call_id: "call-1" } },
      { ...base, event: "node", details: { status: "completed" } },
    ]} />);
    const view = document.createElement("div"); view.innerHTML = html;
    const rows = [...view.querySelectorAll(".execution-row")];
    expect(rows.some(row=>row.textContent?.includes("压缩研究上下文 · 开始"))).toBe(true);
    const model=rows.find(row=>row.textContent?.includes("模型开始调用"))!;
    expect(model).not.toBeUndefined();expect(model.textContent).not.toContain("Token");
    expect(rows.some(row=>row.textContent?.includes("压缩研究上下文 · 完成"))).toBe(true);
  });
  it("未设置总调用上限时只展示实际次数", () => {
    const html = renderToStaticMarkup(<ProcessPanel stages={[]} retrieval={[]} executionEvents={[]}
      usage={{ model_calls: 12, model_call_limit: null, prompt_tokens: 120, completion_tokens: 30,
        total_tokens: 150, usage_source: "provider", cache_hit_count: 0, duration_ms: 640,
        model_duration_ms: 600, budget_exceeded: false, cloud_calls: 0 }} />);
    const view = document.createElement("div"); view.innerHTML = html;
    expect(view.querySelector(".usage-strip strong")?.textContent).toBe("12");
  });
  it("参考流程逐节点显示真实进度，实时时不宣称执行后回放", () => {
    const nodes = ["summarize_history", "rewrite_query", "orchestrator", "tools", "should_compress_context", "compress_context", "fallback_response", "collect_answer", "aggregate_answers"];
    const html = renderToStaticMarkup(<ProcessPanel stages={[]} retrieval={[]} executionEvents={nodes.map((node) => ({
      request_id: "r", thread_id: "t", node, event: "node", replayed: false, loop_protocol_version: "reference.v1",
    }))} />);
    for (const label of ["整理会话历史", "问题补全与拆分", "研究决策", "执行工具", "检查研究上下文容量", "压缩研究上下文", "研究边界收尾", "收集分支答案", "汇总最终答案"]) expect(html).toContain(label);
    expect(html).toContain("实时更新");
    expect(html).not.toContain("执行后回放");
    expect(html).not.toContain("答案核验");
  });
  it("显示实际用量和预算原因，不展示提示词", () => {
    const html = renderToStaticMarkup(<ProcessPanel stages={[]} retrieval={[]} executionEvents={[]}
      usage={{ model_calls: 2, model_call_limit: 2, prompt_tokens: 120, completion_tokens: 30,
        total_tokens: 150, usage_source: "provider", cache_hit_count: 1, duration_ms: 640,
        model_duration_ms: 600, budget_exceeded: true, cloud_calls: 0 }}
      notice="本轮调用预算已用尽，尚未完成回答。" />);
    expect(html).toContain("150");
    expect(html).toContain("2 / 2");
    expect(html).toContain("预算已用尽");
    expect(html).not.toContain("prompt:");
  });
  it("区分模型动作与程序边界，显示分支和回放而不假称证据已保留", () => {
    const base = { request_id: "r", thread_id: "t", branch_id: "B2", replayed: true };
    const html = renderToStaticMarkup(<ProcessPanel stages={[]} retrieval={[]} executionEvents={[
      { ...base, node: "orchestrator", event: "agent_decision", decision_source: "model",
        details: { action: "tools", tool_calls: [{ name: "search_child_chunks", args: { query: "恢复步骤" } }] } },
      { ...base, node: "runtime_guard", event: "runtime_guard", decision_source: "runtime_guard",
        details: { stop_reason: "timeout" } },
    ]} />);
    expect(html).toContain("B2 · 模型");
    expect(html).toContain("搜索：恢复步骤");
    expect(html).toContain("B2 · 程序边界");
    expect(html).toContain("达到时间上限");
    expect(html).toContain("执行后回放");
  });

  it("补全与拆分显示缓存和动作来源，不声称关系来自模型", () => {
    const html = renderToStaticMarkup(<ProcessPanel stages={[]} retrieval={[]} executionEvents={[
      { request_id: "r", thread_id: "t", node: "prepare_query", event: "query_rewritten", decision_source: "cache",
        source: "cache", relation_source: "action", action: "new_question", replayed: true, query: "原问题" },
      { request_id: "r", thread_id: "t", node: "prepare_query", event: "query_rewritten", decision_source: "runtime_guard",
        source: "safe_fallback", relation_source: "pending_state", action: "auto", replayed: true },
    ]} />);
    expect(html).toContain("问题补全与拆分");
    expect(html).toContain("缓存复用");
    expect(html).toContain("用户选择新问题");
    expect(html).toContain("自动继续补充");
    expect(html).toContain("执行后回放");
    expect(html).not.toContain("模型意图");
    expect(html).not.toContain("查询分析");
  });
});
