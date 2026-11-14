import { act } from "react";
import { afterEach,beforeEach,describe,expect,it,vi } from "vitest";
import { useServiceHealth } from "../hooks/use-service-health";
import { mount,prepareDom } from "../test/dom";
import { AppLayout } from "./AppLayout";
vi.mock("../hooks/use-service-health",()=>({useServiceHealth:vi.fn()}));
const health=vi.mocked(useServiceHealth);let view:Awaited<ReturnType<typeof mount>>|undefined;
beforeEach(()=>{prepareDom();localStorage.clear();health.mockReturnValue({state:"online",indexReady:true});});
afterEach(async()=>{await view?.unmount();view=undefined;vi.restoreAllMocks();localStorage.clear();});
describe("公共导航",()=>{
  it("保留导航回调、当前页和退出，折叠保持可访问名称",async()=>{
    const navigate=vi.fn();const logout=vi.fn();view=await mount(<AppLayout path="/knowledge" onNavigate={navigate} onLogout={logout}><p>原页面内容</p></AppLayout>);
    const nav=view.container.querySelector('nav[aria-label="主导航"]')!;expect(nav).not.toBeNull();expect(nav.querySelector('[aria-current="page"]')?.textContent).toContain("知识库");
    expect(nav.querySelectorAll("button")).toHaveLength(2);expect(nav.querySelector('[aria-label="运行日志"]')).toBeNull();
    await act(async()=>(nav.querySelector('[aria-label="问答台"]') as HTMLButtonElement).click());expect(navigate).toHaveBeenCalledWith("/chat");
    await act(async()=>(view!.container.querySelector('[aria-label="折叠导航"]') as HTMLButtonElement).click());expect(localStorage.getItem("wenmai.sidebar.collapsed.v1")).toBe("true");
    expect(view.container.querySelector('[aria-label="退出当前会话"]')).not.toBeNull();await act(async()=>(view!.container.querySelector('[aria-label="退出当前会话"]') as HTMLButtonElement).click());expect(logout).toHaveBeenCalledOnce();
  });
  it.each([[{state:"checking",indexReady:null},"正在检查"],[{state:"online",indexReady:false},"索引未就绪"],[{state:"offline",indexReady:null},"服务不可连接"]] as const)("健康状态%s不生成虚假在线说明",async(value,text)=>{
    health.mockReturnValue(value);view=await mount(<AppLayout path="/chat" onNavigate={()=>{}} onLogout={()=>{}}><p>内容</p></AppLayout>);
    expect(view.container.textContent).toContain(text);expect(view.container.textContent).not.toContain("本地服务在线");expect(view.container.textContent).not.toContain("本地知识模式");
  });
  it("存储不可用时导航仍可折叠",async()=>{
    vi.spyOn(Storage.prototype,"getItem").mockImplementation(()=>{throw new Error("unavailable");});vi.spyOn(Storage.prototype,"setItem").mockImplementation(()=>{throw new Error("unavailable");});
    view=await mount(<AppLayout path="/chat" onNavigate={()=>{}} onLogout={()=>{}}>内容</AppLayout>);
    const collapse=view.container.querySelector('[aria-label="折叠导航"]') as HTMLButtonElement;expect(collapse).not.toBeNull();await act(async()=>collapse.click());expect(view.container.querySelector('[aria-label="展开导航"]')).not.toBeNull();
  });
});
