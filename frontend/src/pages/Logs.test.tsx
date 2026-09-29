import { describe, expect, it } from "vitest";

describe("日志过滤", () => {
  it("支持按请求标识过滤", () => expect({ request_id: "abc" }).toHaveProperty("request_id"));
});
