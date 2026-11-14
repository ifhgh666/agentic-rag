import { act } from "react";
import { beforeEach,afterEach,describe,expect,it,vi } from "vitest";
import { getHealth } from "../api/client";
import { mount,prepareDom } from "../test/dom";
import { useServiceHealth } from "./use-service-health";
vi.mock("../api/client",()=>({getHealth:vi.fn()}));
const readHealth=vi.mocked(getHealth);
let view:Awaited<ReturnType<typeof mount>>|undefined;
function Probe(){const value=useServiceHealth();return <output>{JSON.stringify(value)}</output>;}
const ready={status:"ok",service:"pdf-rag-api",index_ready:true};
beforeEach(()=>{prepareDom();vi.useFakeTimers();readHealth.mockReset();});
afterEach(async()=>{await view?.unmount();view=undefined;vi.useRealTimers();vi.restoreAllMocks();});
describe("服务健康状态",()=>{
  it("响应前checking，成功后仅显示真实index_ready",async()=>{
    let finish!:(value:typeof ready)=>void;
    readHealth.mockImplementation(()=>new Promise(done=>{finish=done;}));
    view=await mount(<Probe/>);
    expect(view.container.textContent).toContain('"checking"');
    expect(view.container.textContent).toContain('"indexReady":null');
    await act(async()=>finish(ready));
    expect(JSON.parse(view.container.textContent!)).toEqual({state:"online",indexReady:true});
  });
  it("索引未就绪和服务不可连接分别投影，不沿用旧ready",async()=>{
    readHealth.mockResolvedValueOnce({...ready,index_ready:false});view=await mount(<Probe/>);
    expect(JSON.parse(view.container.textContent!)).toEqual({state:"online",indexReady:false});
    readHealth.mockRejectedValueOnce(new Error("offline"));
    await act(async()=>window.dispatchEvent(new Event("focus")));
    expect(JSON.parse(view.container.textContent!)).toEqual({state:"offline",indexReady:null});
  });
  it("每30秒检查，隐藏时跳过，重新显示时检查",async()=>{
    const visible=vi.spyOn(document,"visibilityState","get").mockReturnValue("visible");
    readHealth.mockResolvedValue(ready);view=await mount(<Probe/>);
    await act(async()=>vi.advanceTimersByTime(30000));expect(readHealth).toHaveBeenCalledTimes(2);
    visible.mockReturnValue("hidden");await act(async()=>vi.advanceTimersByTime(30000));expect(readHealth).toHaveBeenCalledTimes(2);
    visible.mockReturnValue("visible");await act(async()=>document.dispatchEvent(new Event("visibilitychange")));expect(readHealth).toHaveBeenCalledTimes(3);
  });
  it("新请求取消旧请求并忽略其迟到响应，卸载停止轮询",async()=>{
    let oldFinish!:(value:typeof ready)=>void;const signals:AbortSignal[]=[];
    readHealth.mockImplementationOnce(signal=>{signals.push(signal!);return new Promise(done=>{oldFinish=done;});});
    readHealth.mockResolvedValue({...ready,index_ready:false});view=await mount(<Probe/>);
    await act(async()=>window.dispatchEvent(new Event("focus")));expect(signals[0].aborted).toBe(true);
    await act(async()=>oldFinish(ready));expect(JSON.parse(view.container.textContent!)).toEqual({state:"online",indexReady:false});
    const calls=readHealth.mock.calls;const lastSignal=calls[calls.length-1][0]!;
    await view.unmount();view=undefined;expect(lastSignal.aborted).toBe(true);
    await act(async()=>vi.advanceTimersByTime(90000));expect(readHealth).toHaveBeenCalledTimes(2);
  });
});
