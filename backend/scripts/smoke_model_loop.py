"""Two bounded local-model calls against isolated evidence; never changes indexes."""
from pathlib import Path
import argparse
import json
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import Settings
from app.core.model_provider import create_provider, complete_model, token_details

TOOLS = [{"type": "function", "function": {"name": "search_child_chunks",
    "description": "检索试验知识库；先检索才有资料", "parameters": {"type": "object",
    "properties": {"query": {"type": "string"}}, "required": ["query"]}}}]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("output/smoke-loop005/native-protocol.json"))
    parser.add_argument("--loop", action="store_true", help="Exercise the new complete loop with isolated tools")
    args = parser.parse_args()
    settings = Settings(llm_max_output_tokens=768, model_context_window=4096)
    if settings.llm_provider != "ollama":
        raise SystemExit("Local Ollama probe only; no automatic provider fallback")
    provider = create_provider(settings)
    if args.loop:
        from uuid import uuid4
        from langchain_core.tools import StructuredTool
        from app.rag.nodes import ModelAgentLoop
        from app.core.model_call import ModelCallBudget
        from app.rag.graph_state import new_agent_state
        parent, child, document = (str(uuid4()) for _ in range(3))
        def search_child_chunks(query: str, limit: int = 3, request_id: str = ""):
            return {"tool": "search_child_chunks", "query": query, "results": [{
                "parent_id": parent, "child_id": child, "document_id": document,
                "source": "isolated-probe.pdf", "section": {"title": "试验参数"},
                "content": "试验产品的额定功率为12 kW。", "score": 1.0, "retrieval_mode": "hybrid"}]}
        def retrieve_parent_chunks(parent_id: str, request_id: str = ""):
            return {"tool": "retrieve_parent_chunks", "parent_id": parent_id, "document_id": document,
                "source": "isolated-probe.pdf", "section": {"title": "试验参数"},
                "content": "试验产品的额定功率为12 kW。"}
        tools = [StructuredTool.from_function(search_child_chunks, description="检索试验资料"),
                 StructuredTool.from_function(retrieve_parent_chunks, description="读取完整章节")]
        budget = ModelCallBudget(8, 12, {}, timeout_seconds=240)
        state = new_agent_state("试验产品的额定功率是多少？", request_id="isolated-loop-probe")
        print("isolated_loop_started", flush=True)
        result = ModelAgentLoop(settings, tools, provider, budget).run(state)
        data = {"passed": result["status"] == "completed" and "12" in result["final_answer"],
                "status": result["status"], "stop_reason": result.get("stop_reason"),
                "answer": result["final_answer"], "calls": result["model_trace"],
                "events": result["execution_trace"]}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"passed": data["passed"], "calls": len(data["calls"]), "output": str(args.output)}))
        return 0 if data["passed"] else 1
    messages = [{"role": "system", "content": "你是检索助手。先调用搜索工具获取资料，然后根据工具结果回答。不要思考过程。回答只输出JSON：{\"answer\":\"中文答案\",\"citation_id\":\"E1\"}。"},
                {"role": "user", "content": "试验产品额定功率是多少？"}]
    output = {"protocol": "native", "model": settings.ollama_model, "context_window": 4096,
              "output_tokens": 768, "calls": [], "passed": False}
    deadline = time.monotonic() + 240
    try:
        for index in range(2):
            print(f"probe_call_{index+1}_started", flush=True)
            started = time.perf_counter()
            result = complete_model(provider, messages, tools=TOOLS, timeout_seconds=min(120, deadline-time.monotonic()))
            output["calls"].append({"duration_seconds": time.perf_counter()-started,
                "content": result.content, "tool_calls": result.tool_calls, **token_details(messages, result)})
            if index == 0:
                if not result.tool_calls or any(c["name"] != "search_child_chunks" for c in result.tool_calls):
                    raise ValueError("First response did not request the allowed search tool")
                messages.append({"role": "assistant", "content": result.content, "tool_calls": result.tool_calls})
                for call in result.tool_calls:
                    if not str(call["args"].get("query", "")).strip():
                        raise ValueError("Missing query")
                    messages.append({"role": "tool", "name": call["name"], "tool_call_id": call["id"],
                        "content": json.dumps({"results": [{"citation_id": "E1", "content": "试验产品额定功率为12 kW。"}]}, ensure_ascii=False)})
            else:
                parsed = json.loads(result.content)
                output["passed"] = not result.tool_calls and "12" in parsed.get("answer", "") and parsed.get("citation_id") == "E1"
    except Exception as exc:
        output["error"] = f"{type(exc).__name__}: {exc}"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"passed": output["passed"], "calls": len(output["calls"]), "output": str(args.output)}, ensure_ascii=True), flush=True)
    return 0 if output["passed"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
