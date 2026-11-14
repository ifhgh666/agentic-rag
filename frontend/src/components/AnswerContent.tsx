import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Check, Copy } from "lucide-react";
import { Button } from "./ui/button";

export function AnswerContent({text}:{text:string}) {
  return <div className="answer-text markdown-content"><ReactMarkdown skipHtml remarkPlugins={[remarkGfm]} components={{
    img:({alt})=><span className="image-placeholder">[图片：{alt || "未命名图片"}]</span>,
    a:({href,children})=><a href={href || undefined} target="_blank" rel="noopener noreferrer">{children}</a>,
    table:({children})=><div className="markdown-table-scroll" tabIndex={0} aria-label="回答中的表格"><table>{children}</table></div>,
  }}>{text}</ReactMarkdown></div>;
}
export function CopyAnswer({text}:{text:string}) {
  const [feedback,setFeedback]=useState("");
  useEffect(()=>{setFeedback("");},[text]);
  async function copy() {
    try { await navigator.clipboard.writeText(text);setFeedback("已复制"); }
    catch { setFeedback("复制失败，请手动选择正文"); }
  }
  return <div className="answer-actions"><Button type="button" variant="ghost" size="sm" onClick={()=>void copy()} aria-label="复制回答" className="text-muted-foreground">{feedback==="已复制"?<Check aria-hidden="true"/>:<Copy aria-hidden="true"/>}复制回答</Button><span role="status" className="copy-feedback">{feedback}</span></div>;
}
