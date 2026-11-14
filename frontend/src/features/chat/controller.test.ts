import { beforeEach, describe, expect, it } from "vitest";
import type { StreamEvent } from "../../api/client";
import { createChatStore } from "../../stores/chat-store";
import { createChatController } from "./controller";

describe("会话与流式生命周期", () => {
  let store: ReturnType<typeof createChatStore>;
  beforeEach(() => { store = createChatStore(); });
  it("同步锁阻止双重提交，追加用户消息并清空输入", async () => {
    let finish!: () => void; let calls = 0;
    const controller = createChatController(store, async (_q, _t, emit) => {
      calls++; await new Promise<void>(resolve => { finish = resolve; });
      emit({type:"complete",data:{request_id:"r",thread_id:"t",status:"completed"}});
    });
    controller.setDraft("第一题"); const request = controller.send(); void controller.send();
    expect(calls).toBe(1); expect(store.getState().draft).toBe(""); expect(store.getState().turns[0].question).toBe("第一题");
    expect(controller.newSession()).toBe(false); finish(); await request;
  });
  it("累计答案替换且下一轮不清除旧答案和来源", async () => {
    let calls = 0;
    const controller = createChatController(store, async (_q, _t, emit) => {
      const id = `r${++calls}`;
      emit({type:"answer",data:{request_id:id,thread_id:"t",answer:"原",sources:[]}});
      emit({type:"answer",data:{request_id:id,thread_id:"t",answer:`答案${calls}`,sources:[{document_id:id,filename:`文档${calls}.pdf`,section_title:"章节"}]}});
      emit({type:"complete",data:{request_id:id,thread_id:"t",status:"completed"}});
    });
    controller.setDraft("一"); await controller.send(); controller.setDraft("二"); await controller.send();
    expect(store.getState().turns.map(t=>t.answer)).toEqual(["答案1","答案2"]);
    expect(store.getState().turns[0].sources[0].filename).toBe("文档1.pdf");
    expect(store.getState().turns[1].sources[0].filename).toBe("文档2.pdf");
  });
  it("无complete的EOF保留部分答案并恢复原问题", async () => {
    const controller = createChatController(store, async (_q,_t,emit)=> { emit({type:"answer",data:{request_id:"r",thread_id:"t",answer:"部分",sources:[]}}); });
    controller.setDraft(" \n原问题\n "); await controller.send();
    expect(store.getState().turns[0].status).toBe("failed"); expect(store.getState().turns[0].answer).toBe("部分"); expect(store.getState().draft).toBe(" \n原问题\n ");
  });
  it("清空会话会abort并拒绝旧事件，即使旧传输忽略signal", async () => {
    let emitOld!: (event:StreamEvent)=>void; let finish!: ()=>void; let signal:AbortSignal|undefined;
    const controller = createChatController(store, async (_q,_t,emit,_action,s)=>{emitOld=emit;signal=s;await new Promise<void>(resolve=>{finish=resolve;});});
    controller.setDraft("一"); const pending=controller.send(); controller.reset();
    expect(signal?.aborted).toBe(true); emitOld({type:"answer",data:{request_id:"old",thread_id:"old",answer:"迟到",sources:[]}}); finish(); await pending;
    expect(store.getState().turns).toEqual([]); expect(store.getState().threadId).toBeNull();
  });
  it("已绑定请求和线程拒绝不匹配事件", async () => {
    const controller=createChatController(store,async(_q,_t,emit)=>{
      emit({type:"answer",data:{request_id:"r",thread_id:"t",answer:"正确轮",sources:[]}});
      emit({type:"answer",data:{request_id:"wrong",thread_id:"t",answer:"错请求",sources:[]}});
      emit({type:"answer",data:{request_id:"r",thread_id:"wrong",answer:"错线程",sources:[]}});
      emit({type:"complete",data:{request_id:"r",thread_id:"t",status:"completed"}});
    });controller.setDraft("一");await controller.send();expect(store.getState().turns[0].answer).toBe("正确轮");
  });
  it("只接收非空和不超过2000字的文本", async()=>{
    let calls=0;const controller=createChatController(store,async()=>{calls++;});
    controller.setDraft("  ");await controller.send();controller.setDraft("问".repeat(2001));await controller.send();expect(calls).toBe(0);
  });
});
