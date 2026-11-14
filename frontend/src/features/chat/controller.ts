import type { StoreApi } from "zustand/vanilla";
import { messageFromError, streamChat, type StreamEvent } from "../../api/client";
import { chatStore, createTurn, initialSession, type ChatSession, type ChatTurn, type TurnStatus } from "../../stores/chat-store";
import type { ChatAction, ExecutionEvent } from "../../types/api";

const statuses = new Set<TurnStatus>(["completed","partial","insufficient","clarification","cancelled","failed"]);
const nodeProgress:Record<string,string> = { select_tool:"正在判断是否需要查资料", answer_direct:"正在生成回答", summarize_history:"正在整理会话", rewrite_query:"正在分析问题", orchestrator:"正在分析资料", tools:"正在查找资料", should_compress_context:"正在整理资料", compress_context:"正在整理资料", fallback_response:"正在整理回答", collect_answer:"正在汇总资料", aggregate_answers:"正在生成回答" };
const executionTypes = new Set(["query_rewritten","agent_decision","tool_start","tool_call","runtime_guard","hybrid_search","parent_retrieval","budget","node","model_start","model_call"]);

function project(turn:ChatTurn, event:StreamEvent):ChatTurn {
  const next = {...turn};
  if (event.type === "step") next.stages=[...turn.stages,event.data];
  if (event.type === "analysis") { next.analysis=event.data; next.progress=event.data.is_clear ? "正在处理问题" : "需要补充信息"; }
  if (event.type === "retrieval") next.retrieval=event.data.results;
  if (event.type === "tool_result" && !turn.parentResults.some(row=>row.tool_call_id===event.data.tool_call_id && row.parent.parent_id===event.data.parent.parent_id)) next.parentResults=[...turn.parentResults,event.data];
  if (event.type === "usage") next.usage=event.data;
  if (event.type === "answer") { next.answer=event.data.answer; next.sources=event.data.sources; next.progress="正在生成回答"; }
  if (event.type === "clarification" && event.data.pending) next.clarification=event.data.question;
  if (event.type === "error") { next.error=event.data.message; next.progress="本次回答未完成"; }
  if (executionTypes.has(event.type)) {
    const data=event.data as ExecutionEvent;
    // An event with a sequence can be delivered twice by a transport; unnumbered events stay independent.
    if (data.event_sequence == null || !turn.executionEvents.some(row=>row.event_sequence===data.event_sequence)) next.executionEvents=[...turn.executionEvents,data];
    if (["tool_start","hybrid_search","parent_retrieval"].includes(event.type)) next.progress=data.tool==="retrieve_parent_chunks" ? "正在阅读相关章节" : "正在查找资料";
    else if (["node","model_start"].includes(event.type) && !["completed","end"].includes(String(data.details?.status)) && nodeProgress[data.node]) next.progress=nodeProgress[data.node];
  }
  if (event.type === "complete") {
    next.receivedComplete=true;
    next.status=next.error ? "failed" : statuses.has(event.data.status as TurnStatus) ? event.data.status as TurnStatus : "failed";
    next.notice=event.data.reason ?? "";
    if (next.status==="failed" && !next.error) next.error="本次回答未完成，请稍后重试。";
  }
  return next;
}

export function createChatController(store:StoreApi<ChatSession>, transport:typeof streamChat=streamChat) {
  let active:AbortController|null=null;
  let serial=0;
  function reset() {
    const previous=active; active=null;
    store.setState(initialSession(store.getState().generation+1),true);
    previous?.abort();
  }
  function newSession() { if(store.getState().runningTurnId) return false; reset(); return true; }
  function setDraft(draft:string) { if(!store.getState().runningTurnId) store.setState({draft}); }
  function setAction(action:ChatAction) { if(!store.getState().runningTurnId) store.setState({action}); }
  async function send(override?:ChatAction) {
    const state=store.getState(); const action=override ?? state.action; const question=action==="cancel" ? "" : state.draft.trim();
    if(state.runningTurnId || (action!=="cancel" && (!question || state.draft.length>2000)) || (action==="cancel" && !state.pending)) return;
    const id=`turn-${state.generation}-${++serial}`; const generation=state.generation; const abort=new AbortController(); active=abort;
    store.setState({turns:[...state.turns,createTurn(id,question,action,state.threadId)],runningTurnId:id,...(action!=="cancel"?{draft:""}:{})});
    const current=()=>store.getState().generation===generation && store.getState().runningTurnId===id;
    const update=(updater:(turn:ChatTurn)=>ChatTurn)=>store.setState(s=>({turns:s.turns.map(turn=>turn.id===id ? updater(turn) : turn)}));
    try {
      await transport(question,state.threadId,event=>{
        if(!current()) return;
        const data=event.data as {request_id?:string;thread_id?:string};
        const turn=store.getState().turns.find(row=>row.id===id)!;
        if(turn.receivedComplete || (turn.requestId && data.request_id && turn.requestId!==data.request_id) || (turn.threadId && data.thread_id && turn.threadId!==data.thread_id)) return;
        update(row=>project({...row,requestId:row.requestId ?? data.request_id ?? null,threadId:row.threadId ?? data.thread_id ?? null},event));
        if(data.thread_id) store.setState({threadId:data.thread_id});
        if(event.type==="clarification") store.setState(event.data.pending ? {pending:event.data,pendingTurnId:id,action:"auto"} : {pending:null,pendingTurnId:null,action:"auto"});
        if(event.type==="complete" && ["completed","partial","insufficient","cancelled"].includes(event.data.status)) store.setState({pending:null,pendingTurnId:null,action:"auto",...(event.data.status==="cancelled"?{draft:""}:{})});
      },action,abort.signal);
      if(current()) update(row=>row.receivedComplete ? row : {...row,status:"failed",error:row.error || "连接已中断，回答未完成。请检查连接后重试。"});
    } catch(error) {
      if(current()) update(row=>({...row,status:"failed",error:messageFromError(error)}));
    } finally {
      if(current()) {
        const turn=store.getState().turns.find(row=>row.id===id)!;
        store.setState({runningTurnId:null,...(turn.status==="failed" && action!=="cancel" ? {draft:state.draft} : {})});
        if(active===abort) active=null;
      }
    }
  }
  return {setDraft,setAction,send,newSession,reset};
}
export const chatController=createChatController(chatStore);
