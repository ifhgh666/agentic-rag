import { describe, expect, it } from "vitest";

describe("应用基础状态", () => {
  it("测试环境可以运行", () => {
    expect("pdf-rag").toContain("rag");
  });
});
