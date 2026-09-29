import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ProcessPanel } from "./ProcessPanel";

describe("V3-5 过程面板", () => {
  it("显示实际用量和预算原因，不展示提示词", () => {
    const html = renderToStaticMarkup(<ProcessPanel stages={[]} retrieval={[]} executionEvents={[]}
      usage={{ model_calls: 2, model_call_limit: 2, prompt_tokens: 120, completion_tokens: 30,
        total_tokens: 150, usage_source: "provider", cache_hit_count: 1, duration_ms: 640,
        model_duration_ms: 600, budget_exceeded: true, cloud_calls: 0 }}
      notice="模型调用预算已用尽，已返回原文证据。" />);
    expect(html).toContain("150");
    expect(html).toContain("2 / 2");
    expect(html).toContain("预算已用尽");
    expect(html).not.toContain("prompt:");
  });
});
