import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";
import { AxiosError, type AxiosResponse, type InternalAxiosRequestConfig } from "axios";
import { getHealth, listDocuments } from "./client";
import { clearToken, getToken, setToken } from "../auth/session";

const { adapter } = vi.hoisted(() => ({ adapter: vi.fn() }));
vi.mock("axios", async importOriginal => {
  const actual = await importOriginal<typeof import("axios")>();
  return { ...actual, default: { ...actual.default, create: (config: Parameters<typeof actual.default.create>[0]) => {
    const instance = actual.default.create(config);
    instance.defaults.adapter = adapter;
    return instance;
  } } };
});

function response(config: InternalAxiosRequestConfig, data: unknown, status = 200): AxiosResponse {
  return { config, data, status, statusText: String(status), headers: {} };
}
beforeEach(() => { adapter.mockReset(); clearToken(); });
afterEach(() => clearToken());

describe("健康读取的公开契约", () => {
  it("复用现有REST客户端并保留取消信号", async () => {
    const value = { status: "ok", service: "pdf-rag-api", index_ready: false };
    adapter.mockImplementation(async config => response(config, value));
    const controller = new AbortController();
    expect(await getHealth(controller.signal)).toEqual(value);
    expect(adapter.mock.calls[0][0].url).toBe("/health");
    expect(adapter.mock.calls[0][0].signal).toBe(controller.signal);
  });
  it.each([{}, {status:"ok",service:"pdf-rag-api",index_ready:"true"}, {status:"unavailable",service:"pdf-rag-api",index_ready:true}])("无效响应%s不得显示在线", async value => {
    adapter.mockImplementation(async config => response(config, value));
    await expect(getHealth()).rejects.toThrow("服务健康响应无效");
  });
  it("健康401不清令牌，原受保护接口401仍清令牌", async () => {
    adapter.mockImplementation(async config => { throw new AxiosError("unauthorized", "ERR_BAD_REQUEST", config, {}, response(config, {}, 401)); });
    setToken("test-token");
    await expect(getHealth()).rejects.toThrow();
    expect(getToken()).toBe("test-token");
    await expect(listDocuments()).rejects.toThrow();
    expect(getToken()).toBeNull();
  });
});
