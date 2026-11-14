import { describe, expect, it, vi } from "vitest";
import { isVerification, streamChat } from "./client";

describe("SSE 事件", () => {
  it("仅接收结构有效的真实Parent工具原文，保留完整文本与页码", async () => {
    const valid = { request_id: "r", thread_id: "t", tool: "retrieve_parent_chunks", tool_call_id: "call-parent",
      parent: { parent_id: "p", document_id: "d", filename: "设备.pdf", section_title: "恢复", page_start: 4, page_end: 6, text: "完整章节\n末尾信息" } };
    const invalid = [
      { ...valid, tool: "search_child_chunks" }, { ...valid, tool_call_id: null },
      { ...valid, parent: null }, { ...valid, parent: { ...valid.parent, text: null } },
      { ...valid, parent: { ...valid.parent, filename: 7 } },
      { ...valid, parent: { ...valid.parent, page_start: "4" } },
    ];
    const body = [valid, ...invalid].map((data) => `event: tool_result\ndata: ${JSON.stringify(data)}\n\n`).join("");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(body)));
    const parsed: unknown[] = [];
    try {
      await streamChat("原题", "t", (event) => parsed.push(event));
      expect(parsed).toEqual([{ type: "tool_result", data: valid }]);
    } finally { vi.unstubAllGlobals(); }
  });
  it("参考协议仅检查分析结构，保留四问、空问和清晰度不联动的原始事件", async () => {
    const base = { schema_version: 1, request_id: "r", thread_id: "t", is_clear: true,
      relation: "new_question", source: "model", loop_protocol_version: "reference.v1", replayed: false };
    const accepted = [
      { ...base, questions: ["一", "二", "三", "四"] },
      { ...base, questions: [] },
      { ...base, is_clear: false, questions: ["仍有问题"] },
      { ...base, questions: [""] },
    ];
    const rejected = [
      { ...base, questions: "不是数组" }, { ...base, questions: [4] },
      { ...base, is_clear: "true", questions: [] },
      { ...base, loop_protocol_version: undefined, questions: ["一", "二", "三", "四"] },
      { ...base, loop_protocol_version: undefined, is_clear: false, questions: ["仍有问题"] },
    ];
    const body = [...accepted, ...rejected].map((data) => `event: analysis\ndata: ${JSON.stringify(data)}\n\n`).join("");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(body)));
    const parsed: unknown[] = [];
    try {
      await streamChat("原题", "t", (event) => parsed.push(event));
      expect(parsed).toEqual(accepted.map((data) => ({ type: "analysis", data })));
    } finally { vi.unstubAllGlobals(); }
  });
  it("保留参考协议实时节点、累计答案、最终来源与null调用上限", async () => {
    const identity = { request_id: "r", thread_id: "t", loop_protocol_version: "reference.v1", replayed: false };
    const analysis = { ...identity, schema_version: 1, is_clear: true, relation: "clarification", questions: ["设备恢复条件"], source: "model", relation_source: "pending_state", action: "auto" };
    const node = { ...identity, event: "node", node: "aggregate_answers" };
    const partial = { ...identity, answer: "恢复", sources: [] };
    const final = { ...identity, answer: "恢复条件。", sources: [{ document_id: "d", filename: "设备.pdf", section_title: "恢复", page_start: 2 }] };
    const usage = { ...identity, model_calls: 14, model_call_limit: null, prompt_tokens: 100, completion_tokens: 20, total_tokens: 120, usage_source: "provider", cache_hit_count: 0, model_duration_ms: 60, duration_ms: 80, budget_exceeded: false, cloud_calls: 0 };
    const expected = [{ type: "analysis", data: analysis }, { type: "node", data: node }, { type: "answer", data: partial }, { type: "answer", data: final }, { type: "usage", data: usage }];
    const body = expected.map(({ type, data }) => `event: ${type}\ndata: ${JSON.stringify(data)}\n\n`).join("");
    const fetchMock = vi.fn().mockResolvedValue(new Response(body));
    vi.stubGlobal("fetch", fetchMock);
    const parsed: unknown[] = [];
    try {
      await streamChat("PX-200", "t", (event) => parsed.push(event));
      expect(parsed).toEqual(expected);
      expect(JSON.parse(fetchMock.mock.calls[0][1].body as string)).toEqual({ question: "PX-200", thread_id: "t", action: "auto" });
    } finally { vi.unstubAllGlobals(); }
  });
  it("保留诊断排队 node 和唯一终态的顺序", async () => {
    const receipt = { request_id: "r", thread_id: "t", node: "diagnostics", event: "node",
      details: { diagnostic_id: "job", diagnostic_status: "queued", reason: "accepted" } };
    const complete = { request_id: "r", thread_id: "t", status: "completed" };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(
      `event: node\ndata: ${JSON.stringify(receipt)}\n\nevent: complete\ndata: ${JSON.stringify(complete)}\n\n`,
    )));
    const parsed: unknown[] = [];
    try {
      await streamChat("问题", "t", (event) => parsed.push(event));
      expect(parsed).toEqual([{ type: "node", data: receipt }, { type: "complete", data: complete }]);
    } finally { vi.unstubAllGlobals(); }
  });

  const verification = { schema_version: 2, request_id: "r", thread_id: "t", reason: "不评估完整性",
    evidence_status: "found", citation_status: "not_evaluated", numeric_status: "not_evaluated", completeness_status: "not_evaluated" };
  it("聊天入口忽略所有在线核验及评分事件", async () => {
    const block = (type: string, data: unknown) => `event: ${type}\ndata: ${JSON.stringify(data)}\n\n`;
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(
      block("evaluation", { overall: 95 })
      + block("verification", { ...verification, schema_version: 1 })
      + block("verification", { ...verification, completeness_status: "95%" })
      + block("verification", verification)
      + block("answer_evaluation", verification),
    )));
    const parsed: unknown[] = [];
    try {
      await streamChat("问题", "t", (event) => parsed.push(event));
      expect(parsed).toEqual([]);
    } finally { vi.unstubAllGlobals(); }
  });
  it("拒绝带旧综合分的混合核验载荷", () => {
    expect(isVerification(verification)).toBe(true);
    expect(isVerification({ ...verification, overall: 90 })).toBe(false);
    expect(isVerification({ ...verification, faithfulness: 95 })).toBe(false);
    expect(isVerification({ ...verification, completeness_status: "not_applicable" })).toBe(false);
  });
  it("事件块包含事件名和数据", () => {
    const block = "event: complete\ndata: {\"status\":\"completed\"}";
    expect(block).toContain("event: complete");
    expect(block).toContain("data:");
  });

  it("传递 thread_id 并解析执行事件", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(
      'event: tool_call\ndata: {"request_id":"r","thread_id":"t","node":"tools","event":"tool_call","tool":"search_child_chunks"}\n\n',
      { status: 200, headers: { "Content-Type": "text/event-stream" } },
    ));
    vi.stubGlobal("fetch", fetchMock);
    const events: string[] = [];
    await streamChat("问题", "thread-a", (event) => events.push(event.type));
    expect(events).toEqual(["tool_call"]);
    expect(JSON.parse(fetchMock.mock.calls[0][1].body as string)).toMatchObject({ question: "问题", thread_id: "thread-a" });
    vi.unstubAllGlobals();
  });
  it("发送取消动作并解析澄清事件", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(
      'event: clarification\ndata: {"schema_version":1,"thread_id":"t","question":"请补充型号","pending":true,"allowed_actions":["cancel"]}\n\n',
    ));
    vi.stubGlobal("fetch", fetchMock);
    const parsed: string[] = [];
    await streamChat("", "t", (event) => parsed.push(event.type), "cancel");
    expect(JSON.parse(fetchMock.mock.calls[0][1].body as string)).toMatchObject({ question: "", thread_id: "t", action: "cancel" });
    expect(parsed).toEqual(["clarification"]);
    vi.unstubAllGlobals();
  });

  it("保留版本1补全事件的真实来源、调用关联和回放信息", async () => {
    const metadata = { source: "cache", relation_source: "action", action: "new_question", budget_node: "query_analysis", model_call_id: null, replayed: true };
    const analysis = { schema_version: 1, request_id: "r", thread_id: "t", is_clear: true,
      relation: "new_question", questions: ["PN8733 的启动电压是多少？"], ...metadata };
    const rewrite = { request_id: "r", thread_id: "t", node: "prepare_query", event: "query_rewritten",
      query: analysis.questions[0], is_clear: true, decision_source: "cache", ...metadata };
    const block = (type: string, data: unknown) => `event: ${type}\ndata: ${JSON.stringify(data)}\n\n`;
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(block("analysis", analysis) + block("query_rewritten", rewrite))));
    const parsed: unknown[] = [];
    try {
      await streamChat(analysis.questions[0], "t", (event) => parsed.push(event), "new_question");
      expect(parsed).toEqual([{ type: "analysis", data: analysis }, { type: "query_rewritten", data: rewrite }]);
    } finally { vi.unstubAllGlobals(); }
  });

  it("兼容旧版本1分析并忽略未知版本或无效三字段映射", async () => {
    const analysis = { schema_version: 1, request_id: "r", thread_id: "t", is_clear: true,
      relation: "new_question", questions: ["问题"], source: "model" };
    const block = (data: unknown) => `event: analysis\ndata: ${JSON.stringify(data)}\n\n`;
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(block(analysis)
      + block({ ...analysis, schema_version: 9 }) + block({ ...analysis, questions: "问题" })
      + block({ ...analysis, is_clear: false, questions: ["问题"] })
      + block({ ...analysis, relation_source: "model" }))));
    const parsed: unknown[] = [];
    try {
      await streamChat("问题", "t", (event) => parsed.push(event));
      expect(parsed).toEqual([{ type: "analysis", data: analysis }]);
    } finally { vi.unstubAllGlobals(); }
  });
});
