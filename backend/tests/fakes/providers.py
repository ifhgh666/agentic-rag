class FakeEmbedder:
    def __init__(self, vector):
        self.vector = vector

    def embed_many(self, texts):
        return [self.vector for _ in texts]


class FakeGenerator:
    def generate(self, question, context):
        return f"测试答案：{context[:100]}"


class ScriptedModel:
    """Explicit model actions for loop regression; no semantic runtime rules."""
    def __init__(self, *outputs):
        self.outputs = iter(outputs)
        self.calls = []

    def complete(self, messages, *, tools=None, response_schema=None):
        self.calls.append(messages)
        return next(self.outputs)


def query_analysis_payload(questions, *, clear=True, clarification=""):
    """Strict three-field fixture; no relation or procedure intent from a model."""
    return {"is_clear": clear, "questions": questions, "clarification_needed": clarification}


class ScriptedQueryProvider:
    """Test-only entrance output, including malformed payloads and failures."""
    def __init__(self, *outputs):
        self.outputs = iter(outputs)
        self.calls = []
        self.response_schemas = []

    def complete(self, messages, *, tools=None, response_schema=None):
        import json
        from app.core.model_provider import ModelResult
        assert tools is None
        self.calls.append(messages)
        self.response_schemas.append(response_schema)
        payload = next(self.outputs)
        if isinstance(payload, Exception):
            raise payload
        content = json.dumps(payload, ensure_ascii=False) if isinstance(payload, (dict, list)) else payload
        return ModelResult(content, "fake", "scripted-query-v1", 20, 8)


def tool_action(name="search_child_chunks", **args):
    from uuid import uuid4
    from app.core.model_provider import ModelResult
    return ModelResult("", "fake", "script", tool_calls=[
        {"id": str(uuid4()), "name": name, "args": args}])


def terminal_answer(text, quote, citation_id="B1E1"):
    import json
    from app.core.model_provider import ModelResult
    return ModelResult(json.dumps({"status": "answered", "answer": text,
        "citations": [{"citation_id": citation_id, "quote": quote}]}, ensure_ascii=False), "fake", "script")


class ToolAwareProvider:
    """Explicit test model: request a search, then use the supplied terminal script.

    This is a test-only tool decision, never a production fallback. It maps fixture
    E1/E2 IDs to their branch-scoped wire IDs without changing answers or quotes.
    """
    def __init__(self, terminal):
        self.terminal = terminal

    def complete(self, messages, *, tools=None):
        import json
        from dataclasses import replace
        from uuid import uuid4
        from app.core.model_provider import ModelResult

        returned = [m for m in messages if m["role"] == "tool"]
        if tools and not returned:
            question = next(m["content"] for m in messages if m["role"] == "user" and "本分支完整问题：" in m["content"])
            question = question.split("本分支完整问题：", 1)[1].split("\n分支：", 1)[0]
            return ModelResult("", "fake", "tool-script", tool_calls=[{"id": str(uuid4()),
                "name": "search_child_chunks", "args": {"query": question, "limit": 3}}])
        result = self.terminal.complete(messages)
        if returned:
            try:
                payload = json.loads(result.content)
                evidence = [r for m in returned for r in json.loads(m["content"]).get("results", [])]
                mapping = {f"E{i+1}": r["citation_id"] for i, r in enumerate(evidence)}
                for citation in payload.get("citations", []):
                    citation["citation_id"] = mapping.get(citation["citation_id"], citation["citation_id"])
                return replace(result, content=json.dumps(payload, ensure_ascii=False))
            except (ValueError, KeyError):
                pass
        return result

