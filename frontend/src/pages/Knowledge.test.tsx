import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { deleteDocument, listDocuments, uploadDocument } from "../api/client";
import type { DocumentItem } from "../types/api";
import { mount, prepareDom, setInput } from "../test/dom";
import { Knowledge } from "./Knowledge";

vi.mock("../api/client", () => ({ listDocuments: vi.fn(), uploadDocument: vi.fn(), deleteDocument: vi.fn(), messageFromError: (error: Error) => error.message }));
const list = vi.mocked(listDocuments), upload = vi.mocked(uploadDocument), remove = vi.mocked(deleteDocument);
const documentItem = (id: string, filename: string, status: DocumentItem["status"] = "ready"): DocumentItem => ({
  document_id: id, filename, status, size_bytes: 2048, uploaded_at: "2026-10-29T09:00:00Z", parent_count: status === "ready" ? 3 : 0, child_count: status === "ready" ? 12 : 0,
  error_reason: status === "failed" ? "未提取到可用文本" : null,
});
const fixtures = [documentItem("one", "设备手册.PDF"), documentItem("two", "设备规程.pdf", "processing"), documentItem("three", "扫描件.pdf", "failed")];
let view: Awaited<ReturnType<typeof mount>> | undefined;
beforeEach(() => { prepareDom(); list.mockReset().mockResolvedValue(fixtures); upload.mockReset(); remove.mockReset().mockResolvedValue(undefined); });
afterEach(async () => { await view?.unmount(); view = undefined; vi.useRealTimers(); });
async function start() { view = await mount(<Knowledge />); }
function button(label: string) { const element = Array.from(document.querySelectorAll<HTMLButtonElement>("button")).find(node => node.getAttribute("aria-label") === label || node.textContent === label); expect(element, label).toBeTruthy(); return element!; }
async function click(label: string) { await act(async () => button(label).click()); }
function row(filename: string) { return Array.from(view!.container.querySelectorAll("tbody tr")).find(element => element.textContent?.includes(filename)); }
async function select(files: File[]) {
  const field = view!.container.querySelector<HTMLInputElement>('input[type="file"]')!;
  await act(async () => { Object.defineProperty(field, "files", { configurable: true, value: files }); field.dispatchEvent(new Event("change", { bubbles: true })); });
}
async function drop(files: File[]) {
  const zone = view!.container.querySelector('[aria-label="上传 PDF 文档"]')!; expect(zone).toBeTruthy();
  await act(async () => { const event = new Event("drop", { bubbles: true, cancelable: true }); Object.defineProperty(event, "dataTransfer", { value: { files, types: ["Files"] } }); zone.dispatchEvent(event); });
}

describe("Nova知识库文档管理", () => {
  it("展示接口状态、失败原因和真实父子数量", async () => {
    await start(); expect(row("设备手册.PDF")?.textContent).toContain("已就绪");
    expect(row("设备手册.PDF")?.textContent).toContain("3 / 12"); expect(row("设备规程.pdf")?.textContent).toContain("处理中");
    expect(row("扫描件.pdf")?.textContent).toContain("未提取到可用文本");
  });
  it("名称与状态取交集，清除过滤可恢复列表", async () => {
    await start(); const search = view!.container.querySelector<HTMLInputElement>('[aria-label="按文档名称搜索"]'); expect(search).toBeTruthy();
    await setInput(search!, "设备");
    const status = view!.container.querySelector<HTMLSelectElement>('[aria-label="按文档状态筛选"]')!;
    await act(async () => { status.value = "ready"; status.dispatchEvent(new Event("change", { bubbles: true })); });
    expect(row("设备手册.PDF")).toBeTruthy(); expect(row("设备规程.pdf")).toBeUndefined(); expect(row("扫描件.pdf")).toBeUndefined();
    await setInput(search!, "不存在"); expect(view!.container.textContent).toContain("没有匹配的文档");
    await click("清除筛选"); expect(view!.container.querySelectorAll("tbody tr")).toHaveLength(3);
  });
  it("选择或拖入多个文件整批拒绝，非PDF不发送", async () => {
    await start(); const pdf = new File(["%PDF-test"], "a.pdf", { type: "application/pdf" });
    await select([pdf, pdf]); expect(document.querySelector('[role="alert"]')?.textContent).toContain("一个"); expect(upload).not.toHaveBeenCalled();
    await drop([pdf, pdf]); expect(upload).not.toHaveBeenCalled();
    await drop([new File(["text"], "notes.txt", { type: "text/plain" })]); expect(document.querySelector('[role="alert"]')?.textContent).toContain("PDF"); expect(upload).not.toHaveBeenCalled();
  });
  it("单个拖入成功并以刷新后的服务器状态和块数展示", async () => {
    await start(); const pdf = new File(["%PDF-test"], "new.pdf", { type: "application/pdf" });
    upload.mockResolvedValue(documentItem("new", "new.pdf", "processing")); list.mockResolvedValue([documentItem("new", "new.pdf"), ...fixtures]);
    await drop([pdf]); expect(upload).toHaveBeenCalledOnce(); expect(upload).toHaveBeenCalledWith(pdf);
    expect(row("new.pdf")?.textContent).toContain("已就绪"); expect(row("new.pdf")?.textContent).toContain("3 / 12");
  });
  it("同步重复选择只上传一次，失败后同文件可重选", async () => {
    await start(); const pdf = new File(["%PDF-test"], "new.pdf", { type: "application/pdf" });
    let fail!: (error: Error) => void; upload.mockImplementationOnce(() => new Promise((_done, reject) => { fail = reject; }));
    await select([pdf]); await select([pdf]); expect(upload).toHaveBeenCalledOnce();
    await act(async () => fail(new Error("上传暂时不可用"))); expect(document.querySelector('[role="alert"]')?.textContent).toContain("上传暂时不可用");
    upload.mockResolvedValue(documentItem("new", "new.pdf")); await select([pdf]); expect(upload).toHaveBeenCalledTimes(2);
  });
  it("处理中按轮询更新，ready后停止轮询，卸载清理计时", async () => {
    vi.useFakeTimers(); list.mockResolvedValueOnce([fixtures[1]]).mockResolvedValue([documentItem("two", "设备规程.pdf")]);
    await start(); expect(row("设备规程.pdf")?.textContent).toContain("处理中");
    await act(async () => { await vi.advanceTimersByTimeAsync(1800); }); expect(row("设备规程.pdf")?.textContent).toContain("已就绪");
    const count = list.mock.calls.length; await act(async () => { await vi.advanceTimersByTimeAsync(5400); }); expect(list).toHaveBeenCalledTimes(count);
    await view!.unmount(); view = undefined; await vi.advanceTimersByTimeAsync(5400); expect(list).toHaveBeenCalledTimes(count);
  });
  it("刷新失败保留最后成功列表并允许重试", async () => {
    await start(); list.mockRejectedValueOnce(new Error("列表暂时不可用")); await click("刷新文档列表");
    expect(row("设备手册.PDF")).toBeTruthy(); expect(document.querySelector('[role="alert"]')?.textContent).toContain("列表暂时不可用");
    await click("刷新文档列表"); expect(document.querySelector('[role="alert"]')).toBeNull();
  });
  it("删除必须确认，取消不请求并恢复焦点", async () => {
    await start(); button("删除设备手册.PDF").focus(); await click("删除设备手册.PDF");
    expect(document.querySelector('[role="alertdialog"]')?.textContent).toContain("设备手册.PDF"); expect(remove).not.toHaveBeenCalled();
    await click("取消"); expect(remove).not.toHaveBeenCalled(); expect(row("设备手册.PDF")).toBeTruthy();
  });
  it("删除请求防重入、失败保持文档和弹框，重试成功才移除", async () => {
    await start(); await click("删除设备手册.PDF");
    let fail!: (error: Error) => void; remove.mockImplementationOnce(() => new Promise((_done, reject) => { fail = reject; }));
    await click("确认删除"); await click("确认删除"); expect(remove).toHaveBeenCalledOnce(); expect(row("设备手册.PDF")).toBeTruthy();
    await act(async () => fail(new Error("删除失败，请稍后重试")));
    expect(document.querySelector('[role="alertdialog"]')?.textContent).toContain("删除失败"); expect(row("设备手册.PDF")).toBeTruthy();
    list.mockResolvedValue(fixtures.slice(1)); await click("确认删除"); expect(remove).toHaveBeenCalledTimes(2); expect(remove).toHaveBeenLastCalledWith("one"); expect(row("设备手册.PDF")).toBeUndefined();
  });
  it("空库与无匹配区分，首次读取失败也能恢复", async () => {
    list.mockRejectedValueOnce(new Error("无法读取文档列表")); await start(); expect(document.querySelector('[role="alert"]')?.textContent).toContain("无法读取文档列表");
    list.mockResolvedValue([]); await click("刷新文档列表"); expect(view!.container.textContent).toContain("知识库还是空的"); expect(view!.container.textContent).not.toContain("没有匹配的文档");
  });
});
