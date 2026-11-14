import { describe,expect,it } from "vitest";
import { activities } from "./activity";
import type { ExecutionEvent } from "../../types/api";
const event=(name:string,extra:Partial<ExecutionEvent>={}):ExecutionEvent=>({request_id:"r",thread_id:"t",node:"tools",tool:"search_child_chunks",event:name,replayed:false,...extra});
describe("活动身份关联",()=>{
  it("可靠run ID将工具开始和结果更新到同一行",()=>{
    const rows=activities([event("tool_start",{details:{tool_run_id:"a"}}),event("tool_call",{tool_call_id:"call-a",details:{tool_run_id:"a"},duration_ms:20})]);
    expect(rows).toHaveLength(1);expect(rows[0].status).toBe("completed");expect(rows[0].event.tool_call_id).toBe("call-a");expect(rows[0].event.duration_ms).toBe(20);
  });
  it("并行同名工具各自关联，没有ID不能按名称合并",()=>{
    const rows=activities([event("tool_start",{details:{tool_run_id:"a"}}),event("tool_start",{details:{tool_run_id:"b"}}),event("tool_call",{details:{tool_run_id:"b"}}),event("tool_start"),event("tool_call")]);
    expect(rows).toHaveLength(4);expect(rows[0].status).toBe("running");expect(rows[1].status).toBe("completed");
  });
  it("模型调用按ID合并，实际结果与回放标志保留",()=>{
    const rows=activities([event("model_start",{model_call_id:"m",node:"rewrite_query"}),event("model_call",{model_call_id:"m",node:"rewrite_query",replayed:true,details:{input_tokens:12,usage_source:"provider"}})]);
    expect(rows).toHaveLength(1);expect(rows[0].event.replayed).toBe(true);expect(rows[0].event.details?.input_tokens).toBe(12);
  });
});
