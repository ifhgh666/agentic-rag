import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { streamChat, type StreamEvent } from "../api/client";
import { Chat } from "./Chat";
import { chatController } from "../features/chat/controller";

vi.mock("../api/client", () => ({ streamChat: vi.fn(), messageFromError: (error: Error) => error.message }));

let container: HTMLDivElement;
let root: Root;
const mockStream = vi.mocked(streamChat);

beforeEach(async () => {
  (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  mockStream.mockReset();
  chatController.reset();
  container = document.createElement("div"); document.body.append(container);
  root = createRoot(container);
  await act(async () => root.render(<Chat />));
});
afterEach(async () => { await act(async () => {root.unmount();chatController.reset();}); container.remove(); });

function button(label: string) {
  const found = [...container.querySelectorAll("button")].find((item) => item.textContent?.startsWith(label) || item.getAttribute("aria-label")===label);
  if (!found) throw new Error(`missing button: ${label}`);
  return found;
}
async function input(value: string) {
  await act(async () => {
    const field = container.querySelector("textarea")!;
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!.call(field, value);
    field.dispatchEvent(new Event("input", { bubbles: true }));
  });
}
async function submit() {
  await act(async () => { container.querySelector("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })); });
}
async function establishPending() {
  mockStream.mockImplementationOnce(async (_question, _thread, emit) => {
    emit({ type: "clarification", data: {
      schema_version: 1, request_id: "r1", thread_id: "same-thread", pending: true,
      question: "请说明设备型号。", allowed_actions: ["continue_clarification", "new_question", "cancel"],
    } });
    emit({ type: "complete", data: { request_id: "r1", thread_id: "same-thread", status: "clarification" } });
  });
  await input("过流后如何恢复？"); await submit();
}
function emitAnswer(emit: (event: StreamEvent) => void) {
  emit({ type: "analysis", data: { schema_version: 1, request_id: "r2", thread_id: "same-thread", is_clear: true, relation: "new_question", questions: ["问题"], source: "model" } });
  emit({ type: "answer", data: { request_id: "r2", thread_id: "same-thread", answer: "知识库回答", sources: [] } });
  emit({ type: "complete", data: { request_id: "r2", thread_id: "same-thread", status: "completed" } });
}

describe("澄清交互", () => {
  it.each(["next_request", "new_session"])("原文按轮隔离，新会话清除，场景%s", async (reset) => {
    const child = { child_id: "c", parent_id: "p", document_id: "d", filename: "设备.pdf", section_title: "恢复", score: 0.8, content_preview: "旧child预览", text: "旧child完整原文" };
    const nextChild = { ...child, child_id: "c2", content_preview: "第二次预览", text: "第二个child原文" };
    const parentResult = { request_id: "r", thread_id: "t", tool: "retrieve_parent_chunks" as const, tool_call_id: "call-p",
      parent: { parent_id: "p", document_id: "d", filename: "设备.pdf", section_title: "章节", page_start: 2, page_end: 3, text: "旧Parent完整原文" } };
    mockStream.mockImplementationOnce(async (_q, _t, emit) => {
      emit({ type: "retrieval", data: { request_id: "r", thread_id: "t", results: [child] } });
      emit({ type: "retrieval", data: { request_id: "r", thread_id: "t", results: [child, nextChild] } });
      emit({ type: "tool_result", data: parentResult });
      emit({ type: "tool_result", data: parentResult });
      emit({ type: "tool_result", data: { ...parentResult, parent: { ...parentResult.parent, parent_id: "p2", text: "另一分支Parent原文" } } });
      emit({ type: "complete", data: { request_id: "r", thread_id: "t", status: "completed" } });
    });
    await input("恢复条件？"); await submit();
    expect(container.textContent).toContain("旧child完整原文");
    expect(container.textContent).toContain("旧Parent完整原文");
    expect(container.textContent).toContain("第二个child原文");
    expect(container.textContent).toContain("另一分支Parent原文");
    expect(container.querySelectorAll(".retrieval-list details")).toHaveLength(4);
    expect(container.querySelector(".answer-card")).toBeNull();
    if (reset === "new_session") {
      await act(async () => button("新会话").click());
    } else {
      mockStream.mockImplementationOnce(async (_q, _t, emit) => {
        emit({ type: "node", data: { request_id: "r2", thread_id: "t", node: "rewrite_query", event: "node", details: { status: "started" } } });
      });
      await input("另一道题？"); await submit();
    }
    if(reset === "new_session") {
      expect(container.textContent).not.toContain("旧child完整原文");
      expect(container.textContent).not.toContain("旧Parent完整原文");
      expect(container.textContent).not.toContain("第二个child原文");
      expect(container.textContent).not.toContain("另一分支Parent原文");
    } else {
      const turns=container.querySelectorAll(".chat-turn");expect(turns).toHaveLength(2);
      expect(turns[0].textContent).toContain("旧Parent完整原文");
      expect(turns[1].textContent).not.toContain("旧Parent完整原文");
    }
  });
  it("模型启动事件进入实际过程面板，不在答案区显示研究内容", async () => {
    mockStream.mockImplementationOnce(async (_q, _t, emit) => {
      emit({ type: "model_start", data: { request_id: "r", thread_id: "t", node: "orchestrator", event: "model_start", replayed: false, loop_protocol_version: "reference.v1" } });
    });
    await input("恢复条件？"); await submit();
    expect(container.querySelector(".execution-row")?.textContent).toContain("模型开始调用");
    expect(container.querySelector(".execution-row")?.textContent).toContain("研究决策");
    expect(container.querySelector(".answer-card")).toBeNull();
  });
  it("旧服务核验事件不生成在线核验卡，答案仍正常展示", async () => {
    mockStream.mockImplementationOnce(async (_q, _t, emit) => {
      emit({ type: "verification", data: { schema_version: 2, request_id: "r2", thread_id: "same-thread",
        evidence_status: "found", citation_status: "verified", numeric_status: "not_evaluated",
        completeness_status: "not_evaluated", reason: "未评估安全步骤完整性" } });
      emit({ type: "step", data: { request_id: "r2", thread_id: "same-thread", stage: "query_receipt", status: "completed", sequence: 1, duration_ms: 10 } });
      emitAnswer(emit);
    });
    await input("恢复步骤？"); await submit();
    expect(container.querySelector(".verification-card")).toBeNull();
    expect(container.textContent).not.toContain("未评估安全步骤完整性");
    expect(container.textContent).toContain("知识库回答");
    expect(container.textContent).not.toContain("95%");
    const executionDetails = container.querySelector("details.execution-details") as HTMLDetailsElement | null;
    expect(executionDetails).not.toBeNull();
    expect(executionDetails?.open).toBe(false);
    await establishPending();
    expect(container.querySelector(".verification-card")).toBeNull();
  });
  it("澄清单独展示并提供三种选择", async () => {
    await establishPending();
    expect(container.textContent).toContain("请说明设备型号。");
    expect(container.textContent).toContain("直接发送即可补充原问题");
    expect(container.textContent).not.toContain("请先选择");
    expect(container.querySelector(".answer-card")).toBeNull();
    expect(button("继续补充")).toBeDefined();
    expect(button("开始新问题")).toBeDefined();
    expect(button("取消待办")).toBeDefined();
  });
  it("待办默认可直接发送补充，使用auto和原会话", async () => {
    await establishPending();
    expect(button("发送补充").disabled).toBe(true);
    mockStream.mockImplementationOnce(async (_q, _t, emit) => emitAnswer(emit));
    await input("PX-200");
    expect(button("发送补充").disabled).toBe(false);
    await submit();
    expect(mockStream.mock.calls[1]).toEqual(["PX-200", "same-thread", expect.any(Function), "auto", expect.any(AbortSignal)]);
    expect(container.querySelector(".clarification-card")).toBeNull();
  });
  it("累计answer替换当前文本，最终事件更新来源", async () => {
    let emitUpdate: (event: StreamEvent) => void = () => {};
    let finish = () => {};
    mockStream.mockImplementationOnce((_q, _t, emit) => {
      emitUpdate = emit;
      return new Promise<void>((resolve) => { finish = resolve; });
    });
    await input("恢复步骤？"); await submit();
    await act(async () => emitUpdate({ type: "answer", data: { request_id: "r", thread_id: "t", answer: "先断电", sources: [] } }));
    expect(container.querySelector(".answer-text")?.textContent).toBe("先断电");
    await act(async () => emitUpdate({ type: "answer", data: { request_id: "r", thread_id: "t", answer: "先断电，再检查。", sources: [] } }));
    expect(container.querySelector(".answer-text")?.textContent).toBe("先断电，再检查。");
    expect(container.querySelector(".source-strip")).toBeNull();
    await act(async () => {
      emitUpdate({ type: "answer", data: { request_id: "r", thread_id: "t", answer: "先断电，再检查。", sources: [{ document_id: "d", filename: "设备手册.pdf", section_title: "恢复", page_start: 4 }] } });
      emitUpdate({ type: "complete", data: { request_id: "r", thread_id: "t", status: "completed" } });
      finish();
    });
    expect(container.querySelector(".answer-text")?.textContent).toBe("先断电，再检查。");
    expect(container.querySelector(".source-strip")?.textContent).toContain("设备手册.pdf");
    expect(container.querySelector(".source-strip")?.textContent).toContain("第 4 页");
  });
  it.each(["continue_clarification", "new_question"] as const)("按显式动作 %s 提交到同一会话", async (action) => {
    await establishPending();
    await act(async () => button(action === "new_question" ? "开始新问题" : "继续补充").click());
    mockStream.mockImplementationOnce(async (_q, _t, emit) => emitAnswer(emit));
    await input(action === "new_question" ? "运行记录保留多久？" : "PX-200"); await submit();
    expect(mockStream.mock.calls[1][1]).toBe("same-thread");
    expect(mockStream.mock.calls[1][3]).toBe(action);
    expect(container.querySelector(".clarification-card")).toBeNull();
    expect(container.textContent).toContain("知识库回答");
  });
  it("取消不要求输入文字", async () => {
    await establishPending();
    mockStream.mockImplementationOnce(async (_q, _t, emit) => {
      emit({ type: "complete", data: { request_id: "r2", thread_id: "same-thread", status: "cancelled" } });
    });
    await act(async () => button("取消待办").click());
    expect(mockStream.mock.calls[1][0]).toBe("");
    expect(mockStream.mock.calls[1][3]).toBe("cancel");
    expect(container.querySelector(".clarification-card")).toBeNull();
  });
  it("新问题接受后pending=false立即清除旧待办，后续失败也不恢复卡", async () => {
    await establishPending();
    await act(async () => button("开始新问题").click());
    mockStream.mockImplementationOnce(async (_q, _t, emit) => {
      emit({ type: "clarification", data: { schema_version: 1, request_id: "r2", thread_id: "same-thread", pending: false, question: "", allowed_actions: [] } });
      emit({ type: "error", data: { request_id: "r2", thread_id: "same-thread", code: "RAG_PIPELINE_FAILED", message: "问答处理失败" } });
      emit({ type: "complete", data: { request_id: "r2", thread_id: "same-thread", status: "failed" } });
    });
    await input("记录保留多久？"); await submit();
    expect(container.querySelector(".clarification-card")).toBeNull();
    expect(container.querySelector("label")?.textContent).toBe("你想知道什么？");
    expect(container.querySelector('[role="alert"]')?.textContent).toContain("问答处理失败");
  });
  it.each(["partial", "insufficient"])("终态%s清除已解决待办", async (status) => {
    await establishPending();
    mockStream.mockImplementationOnce(async (_q, _t, emit) => {
      emit({ type: "answer", data: { request_id: "r2", thread_id: "same-thread", answer: "具体资料缺口", sources: [] } });
      emit({ type: "complete", data: { request_id: "r2", thread_id: "same-thread", status } });
    });
    await input("PX-200"); await submit();
    expect(container.querySelector(".clarification-card")).toBeNull();
    expect(container.textContent).toContain("具体资料缺口");
  });
  it("分析失败后保留澄清卡供重试", async () => {
    await establishPending();
    mockStream.mockImplementationOnce(async (_q, _t, emit) => {
      emit({ type: "error", data: { request_id: "r2", thread_id: "same-thread", code: "model_unavailable", message: "模型暂时不可用" } });
    });
    await input("PX-200"); await submit();
    expect(container.textContent).toContain("请说明设备型号。");
    expect(container.querySelector('[role="alert"]')?.textContent).toContain("模型暂时不可用");
  });
  it("分析成功但后续处理失败时仍保留待办", async () => {
    await establishPending();
    mockStream.mockImplementationOnce(async (_q, _t, emit) => {
      emit({ type: "analysis", data: { schema_version: 1, request_id: "r2", thread_id: "same-thread", is_clear: true, relation: "clarification", questions: ["PX-200 过流后如何恢复？"], source: "model" } });
      emit({ type: "error", data: { request_id: "r2", thread_id: "same-thread", code: "RAG_PIPELINE_FAILED", message: "问答处理失败" } });
      emit({ type: "complete", data: { request_id: "r2", thread_id: "same-thread", status: "failed" } });
    });
    await input("PX-200"); await submit();
    expect(container.textContent).toContain("请说明设备型号。");
    expect(container.querySelector('[role="alert"]')?.textContent).toContain("问答处理失败");
  });
});
