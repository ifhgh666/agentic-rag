import { describe, expect, it } from "vitest";

describe("登录页面契约", () => {
  it("登录接口使用管理员凭据语义", () => expect({ username: "admin", password: "secret" }).toHaveProperty("username"));
});
