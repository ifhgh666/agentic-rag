import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { useStore } from "zustand";
import { ArrowDown, ArrowUp, BookOpen, ChevronDown, CircleCheck, LoaderCircle, Plus, Search } from "lucide-react";
import { chatStore } from "../stores/chat-store";
import { chatController } from "../features/chat/controller";
import { EvidenceList } from "../features/chat/EvidenceList";
import { AnswerContent, CopyAnswer } from "../components/AnswerContent";
import { Button } from "../components/ui/button";
import { ProcessPanel } from "../components/ProcessPanel";

const terminalText={completed:"回答完成",partial:"部分回答",insufficient:"资料不足",clarification:"需要补充信息",cancelled:"已取消待办",failed:"回答未完成",running:"正在处理"};
export function Chat() {
  const state=useStore(chatStore); const running=Boolean(state.runningTurnId);
  const scrollRef=useRef<HTMLDivElement>(null); const inputRef=useRef<HTMLTextAreaElement>(null); const composing=useRef(false);
  const follow=useRef(true); const [atBottom,setAtBottom]=useState(true);
  const previousRunning=useRef(running);
  useEffect(()=>{
    if(previousRunning.current && !running && follow.current && document.activeElement===document.body) inputRef.current?.focus({preventScroll:true});
    previousRunning.current=running;
  },[running]);
  function scrollToBottom() { const element=scrollRef.current;if(element){element.scrollTop=element.scrollHeight;follow.current=true;setAtBottom(true);} }
  useEffect(()=>{ if(follow.current) scrollToBottom(); },[state.turns]);
  useEffect(()=>{
    const element=scrollRef.current;if(!element || typeof ResizeObserver==="undefined") return;
    const observer=new ResizeObserver(()=>{if(follow.current) scrollToBottom();});observer.observe(element);return()=>observer.disconnect();
  },[]);
  useEffect(()=>{ const field=inputRef.current;if(field){field.style.height="auto";field.style.height=`${Math.min(160,Math.max(56,field.scrollHeight))}px`;} },[state.draft]);
  function send() {if(!running && (state.draft.trim() || state.action==="cancel")){follow.current=true;void chatController.send();}}
  function onKeyDown(event:KeyboardEvent<HTMLTextAreaElement>) {
    if(event.key!=="Enter" || event.shiftKey) return;
    if(composing.current || event.nativeEvent.isComposing || event.nativeEvent.keyCode===229) return;
    event.preventDefault();if(event.repeat) return;send();
  }
  return <section className="chat-workspace" aria-label="知识库问答">
    <header className="chat-toolbar"><div><span className="chat-kicker">与你的知识对话</span><h1>问答台</h1></div><Button type="button" variant="outline" size="sm" onClick={()=>{if(chatController.newSession()) inputRef.current?.focus();}} disabled={running}><Plus aria-hidden="true"/>新会话</Button></header>
    <div ref={scrollRef} className="chat-messages" tabIndex={0} aria-label="对话记录" onScroll={()=>{const element=scrollRef.current!;const near=element.scrollHeight-element.scrollTop-element.clientHeight<80;follow.current=near;setAtBottom(near);}}>
      {state.turns.length===0 ? <div className="chat-empty"><div className="chat-empty-icon"><BookOpen aria-hidden="true"/></div><p className="chat-kicker">文脉 · 知识问答</p><h2>答案，从你的文档中来。</h2><p>提出问题，查找资料，让每一次回答都有来源。</p><span>支持连续追问与原文核对</span></div> : <div className="chat-thread">{state.turns.map(turn=><article className="chat-turn" key={turn.id} data-turn-id={turn.id} aria-label={`问题：${turn.question || "取消待补充问题"}`}>
        <div className="user-message"><span className="sr-only">你的问题：</span>{turn.question || "取消待补充问题"}</div>
        <div className="assistant-message"><span className="assistant-avatar" aria-hidden="true"><BookOpen/></span><div className="assistant-body">
          <div className="turn-status" role="status">{turn.status==="running" ? <LoaderCircle aria-hidden="true" className="status-spinner"/> : turn.status==="completed"?<CircleCheck aria-hidden="true"/>:<Search aria-hidden="true"/>}<span>{turn.status==="running"?turn.progress:terminalText[turn.status]}</span></div>
          {turn.answer && <div className="answer-card"><AnswerContent text={turn.answer}/><CopyAnswer text={turn.answer}/></div>}
          {turn.clarification && <div className={state.pendingTurnId===turn.id?"assistant-clarification clarification-card":"assistant-clarification"}><p>{turn.clarification}</p>{state.pendingTurnId===turn.id && state.pending && <><div className="clarification-actions">
            {state.pending.allowed_actions.includes("continue_clarification") && <Button variant="outline" size="sm" disabled={running} aria-pressed={state.action==="continue_clarification"} onClick={()=>{chatController.setAction("continue_clarification");inputRef.current?.focus();}}>继续补充</Button>}
            {state.pending.allowed_actions.includes("new_question") && <Button variant="ghost" size="sm" disabled={running} aria-pressed={state.action==="new_question"} onClick={()=>{chatController.setAction("new_question");inputRef.current?.focus();}}>开始新问题</Button>}
            {state.pending.allowed_actions.includes("cancel") && <Button variant="ghost" size="sm" disabled={running} onClick={()=>void chatController.send("cancel")}>取消待办</Button>}
          </div><p className="clarification-hint">{state.action==="new_question"?"下一条消息将作为新问题。":"直接发送即可补充原问题。"}</p></>}</div>}
          {turn.error && <p className="chat-error" role="alert">{turn.error}</p>}
          {turn.notice && !turn.error && <p className="chat-notice">{turn.notice}</p>}
          <EvidenceList sources={turn.sources} retrieval={turn.retrieval} parentResults={turn.parentResults}/>
          {(turn.executionEvents.length>0 || turn.stages.length>0 || turn.analysis || turn.usage) && <details className="execution-details"><summary><Search aria-hidden="true"/><span>查看执行过程</span><ChevronDown aria-hidden="true" className="details-chevron"/></summary><ProcessPanel stages={turn.stages} executionEvents={turn.executionEvents} analysis={turn.analysis} usage={turn.usage}/>{turn.requestId && <p className="technical-id">请求 {turn.requestId} · 会话 {turn.threadId}</p>}</details>}
        </div></div>
      </article>)}</div>}
    </div>
    <div className="chat-composer-area">{!atBottom && <Button variant="outline" size="sm" type="button" onClick={scrollToBottom} className="back-to-bottom"><ArrowDown aria-hidden="true"/>回到最新消息</Button>}
      <form className="chat-composer" onSubmit={event=>{event.preventDefault();send();}} aria-busy={running}>
        <label htmlFor="question" className="sr-only">{state.pending && state.action!=="new_question"?"补充信息":"你想知道什么？"}</label>
        <textarea ref={inputRef} id="question" rows={2} value={state.draft} onChange={event=>chatController.setDraft(event.target.value)} onKeyDown={onKeyDown} onCompositionStart={()=>{composing.current=true;}} onCompositionEnd={()=>{composing.current=false;}} maxLength={2000} disabled={running} placeholder={state.pending && state.action!=="new_question"?"补充一下问题中的信息…":"向你的知识库提问…"}/>
        <div className="composer-foot"><span className="composer-hint">Enter 发送<span> · Shift+Enter 换行</span></span><div><span className="character-count">{state.draft.length} / 2000</span><Button type="submit" size="icon" aria-label={state.pending && state.action!=="new_question"?"发送补充":"发送问题"} disabled={running || !state.draft.trim() || state.draft.length>2000}>{running?<LoaderCircle aria-hidden="true" className="status-spinner"/>:<ArrowUp aria-hidden="true"/>}</Button></div></div>
      </form><p className="composer-disclaimer">回答依据知识库资料生成，请结合来源核对。</p>
    </div>
  </section>;
}
