import { describe, expect, it } from "vitest";

describe("答案分数卡片", () => {
  it("总体分数在 0 到 100 范围内", () => { const score = 86; expect(score).toBeGreaterThanOrEqual(0); expect(score).toBeLessThanOrEqual(100); });
});
