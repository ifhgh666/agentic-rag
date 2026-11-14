import { afterEach,describe,expect,it,vi } from "vitest";
import { streamChat } from "./client";
afterEach(()=>vi.restoreAllMocks());
describe("流式读取清理",()=>{
  it("传递AbortSignal并在正常结束后取消/释放reader",async()=>{
    const reader={read:vi.fn().mockResolvedValue({done:true}),cancel:vi.fn().mockResolvedValue(undefined),releaseLock:vi.fn()};
    const fetcher=vi.spyOn(globalThis,"fetch").mockResolvedValue({ok:true,body:{getReader:()=>reader}} as unknown as Response);
    const controller=new AbortController();await streamChat("问题",null,()=>{},"auto",controller.signal);
    expect(fetcher.mock.calls[0][1]?.signal).toBe(controller.signal);expect(reader.cancel).toHaveBeenCalledOnce();expect(reader.releaseLock).toHaveBeenCalledOnce();
  });
  it("读取失败且cancel也失败时保留原错误并释放锁",async()=>{
    const reader={read:vi.fn().mockRejectedValue(new Error("original-read-error")),cancel:vi.fn().mockRejectedValue(new Error("cancel-error")),releaseLock:vi.fn()};
    vi.spyOn(globalThis,"fetch").mockResolvedValue({ok:true,body:{getReader:()=>reader}} as unknown as Response);
    await expect(streamChat("问题",null,()=>{})).rejects.toThrow("original-read-error");expect(reader.releaseLock).toHaveBeenCalledOnce();
  });
  it("收到complete就释放读取，不等待服务端关闭连接",async()=>{
    const value=new TextEncoder().encode('event: complete\ndata: {"request_id":"r","thread_id":"t","status":"completed"}\n\n');
    const reader={read:vi.fn().mockResolvedValueOnce({done:false,value}),cancel:vi.fn().mockResolvedValue(undefined),releaseLock:vi.fn()};
    vi.spyOn(globalThis,"fetch").mockResolvedValue({ok:true,body:{getReader:()=>reader}} as unknown as Response);
    const emit=vi.fn();await streamChat("问题",null,emit);expect(reader.read).toHaveBeenCalledOnce();expect(emit).toHaveBeenCalledWith(expect.objectContaining({type:"complete"}));expect(reader.releaseLock).toHaveBeenCalledOnce();
  });
});
