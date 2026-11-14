import { act } from "react";
import { afterEach,beforeEach,describe,expect,it,vi } from "vitest";
import App from "./App";
import { streamChat,logout,type StreamEvent } from "./api/client";
import { setToken,clearToken } from "./auth/session";
import { chatStore } from "./stores/chat-store";
import { chatController } from "./features/chat/controller";
import { mount,prepareDom } from "./test/dom";
vi.mock("./api/client",()=>({streamChat:vi.fn(),logout:vi.fn().mockResolvedValue(undefined),messageFromError:(error:Error)=>error.message}));
vi.mock("./hooks/use-service-health",()=>({useServiceHealth:()=>({state:"online",indexReady:true})}));
vi.mock("./pages/Knowledge",()=>({Knowledge:()=> <p>文档页面</p>}));
vi.mock("./pages/Login",()=>({Login:()=> <h1>登录页</h1>}));
let view:Awaited<ReturnType<typeof mount>>|undefined;
beforeEach(()=>{prepareDom();chatController.reset();localStorage.clear();setToken("test-token");window.history.replaceState(null,"","/#/chat");vi.mocked(streamChat).mockReset();vi.mocked(logout).mockReset().mockResolvedValue(undefined);});
afterEach(async()=>{await view?.unmount();view=undefined;chatController.reset();localStorage.clear();});
describe("应用路由和会话边界",()=>{
  it("旧日志地址替换为问答，导航只保留两项",async()=>{
    window.history.replaceState(null,"","/#/logs");view=await mount(<App/>);
    expect(window.location.hash).toBe("#/chat");expect(view.container.querySelectorAll('nav[aria-label="主导航"] button')).toHaveLength(2);
    expect(view.container.textContent).not.toContain("运行日志");
  });
  it("切换知识库不取消流，回来后继续显示同一轮结果",async()=>{
    let emit!:(event:StreamEvent)=>void;let finish!:()=>void;
    vi.mocked(streamChat).mockImplementation(async(_q,_t,onEvent)=>{emit=onEvent;await new Promise<void>(resolve=>{finish=resolve;});});
    view=await mount(<App/>);await act(async()=>chatController.setDraft("问题"));
    await act(async()=>{view!.container.querySelector("form")!.dispatchEvent(new Event("submit",{bubbles:true,cancelable:true}));});
    await act(async()=>(view!.container.querySelector('nav[aria-label="主导航"] [aria-label="知识库"]') as HTMLButtonElement).click());
    await act(async()=>window.dispatchEvent(new HashChangeEvent("hashchange")));
    expect(view.container.textContent).toContain("文档页面");expect(chatStore.getState().runningTurnId).not.toBeNull();
    await act(async()=>{emit({type:"answer",data:{request_id:"r",thread_id:"t",answer:"切页后结果",sources:[]}});emit({type:"complete",data:{request_id:"r",thread_id:"t",status:"completed"}});finish();});
    await act(async()=>(view!.container.querySelector('nav[aria-label="主导航"] [aria-label="问答台"]') as HTMLButtonElement).click());
    await act(async()=>window.dispatchEvent(new HashChangeEvent("hashchange")));
    expect(view.container.querySelector(".answer-text")?.textContent).toContain("切页后结果");
  });
  it("退出立即清空，logout接口等待期间也已回到登录页",async()=>{
    let finish!:()=>void;vi.mocked(logout).mockImplementation(()=>new Promise<void>(resolve=>{finish=resolve;}));
    view=await mount(<App/>);await act(async()=>chatController.setDraft("未发送草稿"));
    await act(async()=>(view!.container.querySelector('[aria-label="退出当前会话"]') as HTMLButtonElement).click());
    expect(view.container.textContent).toBe("登录页");expect(chatStore.getState().draft).toBe("");await act(async()=>finish());
  });
  it("受保护接口清除认证时同步清空内存",async()=>{
    view=await mount(<App/>);await act(async()=>chatController.setDraft("草稿"));await act(async()=>clearToken());
    expect(view.container.textContent).toBe("登录页");expect(chatStore.getState().draft).toBe("");
  });
});
