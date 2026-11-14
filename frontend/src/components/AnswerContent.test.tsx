import { act } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe,expect,it,vi } from "vitest";
import { AnswerContent,CopyAnswer } from "./AnswerContent";
import { mount,prepareDom } from "../test/dom";
describe("答案安全与复制",()=>{
  it("支持列表代码和表格，不输出HTML脚本或远程图片",()=>{
    const html=renderToStaticMarkup(<AnswerContent text={'## 条件\n\n- 一\n- 二\n\n| 型号 | 时间 |\n| --- | --- |\n| PX | 72h |\n\n```ts\nconst x = 1\n```\n\n<script>alert(1)</script>\n\n![远程图](https://example.invalid/track.png)\n\n[坏链接](javascript:alert)\n\n[正常链接](https://example.com)'} />);
    const box=document.createElement("div");box.innerHTML=html;
    expect(box.querySelector("h2")?.textContent).toBe("条件");expect(box.querySelectorAll("li")).toHaveLength(2);expect(box.querySelector("table")).not.toBeNull();expect(box.querySelector("pre code")?.textContent).toContain("const x = 1");
    expect(box.querySelector("script,img")).toBeNull();expect(box.textContent).toContain("图片：远程图");expect(html).not.toContain('href="javascript:');expect(box.querySelector('a[href="https://example.com"]')?.getAttribute("rel")).toContain("noopener");
  });
  it.each([true,false])("复制原始Markdown，成功和失败均反馈：%s",async(success)=>{
    prepareDom();const write=success?vi.fn().mockResolvedValue(undefined):vi.fn().mockRejectedValue(new Error("denied"));
    const original=Object.getOwnPropertyDescriptor(navigator,"clipboard");Object.defineProperty(navigator,"clipboard",{value:{writeText:write},configurable:true});
    const view=await mount(<CopyAnswer text="**原始正文**"/>);
    try {await act(async()=>(view.container.querySelector("button") as HTMLButtonElement).click());expect(write).toHaveBeenCalledWith("**原始正文**");expect(view.container.textContent).toContain(success?"已复制":"复制失败");}
    finally {await view.unmount();if(original)Object.defineProperty(navigator,"clipboard",original);else Reflect.deleteProperty(navigator,"clipboard");}
  });
});
