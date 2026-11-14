import { act } from "react";
import { afterEach,beforeEach,describe,expect,it,vi } from "vitest";
import { login } from "../api/client";
import { clearToken,getToken } from "../auth/session";
import { mount,prepareDom,setInput } from "../test/dom";
import { Login } from "./Login";
vi.mock("../api/client",()=>({login:vi.fn(),messageFromError:(error:Error)=>error.message}));
const authenticate=vi.mocked(login);let view:Awaited<ReturnType<typeof mount>>;
const onSuccess=vi.fn();
beforeEach(async()=>{prepareDom();clearToken();authenticate.mockReset();onSuccess.mockReset();view=await mount(<Login onSuccess={onSuccess}/>);});
afterEach(async()=>{await view.unmount();clearToken();});
async function enterPassword(){await setInput(view.container.querySelector('input[autocomplete="current-password"]')!,"preview-password");}
async function submit(twice=false){await act(async()=>{const form=view.container.querySelector("form")!;form.dispatchEvent(new Event("submit",{bubbles:true,cancelable:true}));if(twice)form.dispatchEvent(new Event("submit",{bubbles:true,cancelable:true}));});}
describe("管理员登录",()=>{
  it("只显示居中登录内容，密码切换不提交或清空内容",async()=>{
    expect(view.container.querySelector("h1")?.textContent).toBe("登录工作台");expect(view.container.querySelector(".login-art")).toBeNull();
    await enterPassword();const show=view.container.querySelector('button[aria-label="显示密码"]') as HTMLButtonElement;
    expect(show).not.toBeNull();await act(async()=>show.click());
    expect(view.container.querySelector('input[autocomplete="current-password"]')?.getAttribute("type")).toBe("text");
    expect((view.container.querySelector('input[autocomplete="current-password"]') as HTMLInputElement).value).toBe("preview-password");expect(authenticate).not.toHaveBeenCalled();
  });
  it("登录成功沿用token和回调，阻止同步重复提交",async()=>{
    let finish!:(value:{access_token:string;user:{username:string}})=>void;
    authenticate.mockImplementation(()=>new Promise(done=>{finish=done;}));
    await enterPassword();await submit(true);expect(authenticate).toHaveBeenCalledTimes(1);expect(authenticate).toHaveBeenCalledWith("admin","preview-password");
    expect(view.container.querySelector<HTMLButtonElement>('button[type="submit"]')?.disabled).toBe(true);
    await act(async()=>finish({access_token:"test-token",user:{username:"admin"}}));expect(getToken()).toBe("test-token");expect(onSuccess).toHaveBeenCalledTimes(1);expect(JSON.stringify(localStorage)).not.toContain("preview-password");
  });
  it("认证失败显示错误并释放提交",async()=>{
    authenticate.mockRejectedValue(new Error("账号或密码不正确"));await enterPassword();await submit();
    expect(view.container.querySelector('[role="alert"]')?.textContent).toContain("账号或密码不正确");
    expect(view.container.querySelector<HTMLButtonElement>('button[type="submit"]')?.disabled).toBe(false);expect(getToken()).toBeNull();expect(onSuccess).not.toHaveBeenCalled();
  });
});
