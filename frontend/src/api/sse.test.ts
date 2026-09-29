import { describe, expect, it, vi } from "vitest";
import { streamChat } from "./client";

describe("SSE 事件", () => {
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
});
