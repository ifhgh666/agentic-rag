import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ScoreCard } from "./ScoreCard";
import type { VerificationResult } from "../types/api";

const result: VerificationResult = {
  schema_version: 2, request_id: "r", thread_id: "t", evidence_status: "found",
  citation_status: "verified", numeric_status: "not_evaluated", completeness_status: "not_evaluated",
  reason: "引文可定位，不代表答案完整。",
};

describe("证据核验卡", () => {
  it("展示四个状态，绝不合成总分", () => {
    const html = renderToStaticMarkup(createElement(ScoreCard, { verification: result }));
    expect(html).toContain("证据核验");
    expect(html).toContain("引文定位");
    expect(html).toContain("未评估");
    expect(html).not.toContain("总体可信度");
    expect(html).not.toContain("/ 100");
    expect(html).not.toContain("完整可信");
  });
  it("证据不足时保持明确提示", () => {
    const html = renderToStaticMarkup(createElement(ScoreCard, {
      verification: { ...result, evidence_status: "insufficient", citation_status: "not_applicable" },
    }));
    expect(html).toContain("证据不足");
    expect(html).toContain("不适用");
  });
  it("引文已定位时也不暗示事实或步骤完整，保留未评估说明", () => {
    const html = renderToStaticMarkup(createElement(ScoreCard, { verification: result }));
    expect(html).toContain("数值条件");
    expect(html).toContain("步骤完整性");
    expect(html).toContain("来源可定位不等于事实正确或答案完整");
    expect((html.match(/未评估/g) ?? []).length).toBe(2);
    expect(html).not.toContain("完整性 100");
    expect(html).not.toContain("总体可信度");
  });
});
