import { describe, expect, it, beforeEach } from "vitest";
import { clearToken, getToken, isAuthenticated, setToken } from "./session";

describe("会话令牌", () => {
  beforeEach(() => clearToken());
  it("可以保存和清除令牌", () => { setToken("test-token"); expect(getToken()).toBe("test-token"); expect(isAuthenticated()).toBe(true); clearToken(); expect(isAuthenticated()).toBe(false); });
});
