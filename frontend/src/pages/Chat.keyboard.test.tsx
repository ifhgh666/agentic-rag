import { act } from "react";
import { afterEach,beforeEach,describe,expect,it,vi } from "vitest";
import { streamChat } from "../api/client";
import { Chat } from "./Chat";
import { chatController } from "../features/chat/controller";
import { mount,prepareDom } from "../test/dom";
vi.mock("../api/client",()=>({streamChat:vi.fn(),messageFromError:(error:Error)=>error.message}));
let view:Awaited<ReturnType<typeof mount>>;
beforeEach(async()=>{prepareDom();chatController.reset();vi.mocked(streamChat).mockReset();view=await mount(<Chat/>);});
afterEach(async()=>{await view.unmount();chatController.reset();});
async function draft(value:string) {await act(async()=>chatController.setDraft(value));}
async function key(init:KeyboardEventInit) {await act(async()=>view.container.querySelector("textarea")!.dispatchEvent(new KeyboardEvent("keydown",{bubbles:true,cancelable:true,key:"Enter",...init})));}
describe("发送快捷键",()=>{
  it.each([{shiftKey:true},{isComposing:true},{keyCode:229},{repeat:true}])("%s不会发送",async(init)=>{await draft("问题");await key(init);expect(streamChat).not.toHaveBeenCalled();});
  it("Enter立即发送，长按/双击/运行中提交都不能重复",async()=>{
    let done!:()=>void;vi.mocked(streamChat).mockImplementation(async(_q,_t,emit)=>{await new Promise<void>(resolve=>{done=resolve;});emit({type:"complete",data:{request_id:"r",thread_id:"t",status:"completed"}});});
    await draft("问题");await key({});await key({repeat:true});await act(async()=>{view.container.querySelector("form")!.dispatchEvent(new Event("submit",{bubbles:true,cancelable:true}));});
    expect(streamChat).toHaveBeenCalledTimes(1);expect(view.container.querySelector("textarea")?.value).toBe("");expect(view.container.querySelector("textarea")?.disabled).toBe(true);
    await act(async()=>{done();});
    expect(document.activeElement).toBe(view.container.querySelector("textarea"));
  });
});
