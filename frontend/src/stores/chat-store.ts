import { createStore } from "zustand/vanilla";
import type { AnalysisEvent, ChatAction, ClarificationEvent, ExecutionEvent, ParentToolResult, RetrievalResult, SourceRef, StageEvent, UsageEvent } from "../types/api";

export type TurnStatus = "running" | "completed" | "partial" | "insufficient" | "clarification" | "cancelled" | "failed";
export interface ChatTurn {
  id: string;
  requestId: string | null;
  threadId: string | null;
  question: string;
  action: ChatAction;
  answer: string;
  sources: SourceRef[];
  stages: StageEvent[];
  analysis: AnalysisEvent | null;
  retrieval: RetrievalResult[];
  parentResults: ParentToolResult[];
  executionEvents: ExecutionEvent[];
  usage: UsageEvent | null;
  clarification: string;
  error: string;
  notice: string;
  status: TurnStatus;
  progress: string;
  receivedComplete: boolean;
}
export interface ChatSession {
  threadId: string | null;
  draft: string;
  pending: ClarificationEvent | null;
  pendingTurnId: string | null;
  action: ChatAction;
  turns: ChatTurn[];
  runningTurnId: string | null;
  generation: number;
}
export const initialSession = (generation = 0): ChatSession => ({ threadId:null, draft:"", pending:null, pendingTurnId:null, action:"auto", turns:[], runningTurnId:null, generation });
export const createChatStore = () => createStore<ChatSession>()(() => initialSession());
export const chatStore = createChatStore();
export const createTurn = (id:string, question:string, action:ChatAction, threadId:string|null):ChatTurn => ({
  id, question, action, threadId, requestId:null, answer:"", sources:[], stages:[], analysis:null,
  retrieval:[], parentResults:[], executionEvents:[], usage:null, clarification:"", error:"", notice:"",
  status:"running", progress:"正在连接…", receivedComplete:false,
});
