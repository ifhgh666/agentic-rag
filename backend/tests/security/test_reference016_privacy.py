import json
from types import SimpleNamespace

from langchain_core.messages import AIMessage

from app.core.pipeline import RagPipeline
from app.observability.logger import StructuredLogger


def test_public_custom_observations_use_an_allowlist(settings):
    secret = 'PRIVATE_PROMPT_SENTINEL'
    class Graph:
        settings = None
        retriever = None
        def stream_run(self, *args):
            yield {'kind': 'custom', 'data': {'event': 'model_call', 'node': 'rewrite_query', 'details': {
                'model_call_id': 'model-observed', 'input_tokens': 3, 'output_tokens': 2,
                'input_messages': [{'content': secret}], 'api_key': 'sk-private', 'private_reasoning': secret}}}
            yield {'kind': 'final', 'data': {'state': {'messages': [AIMessage(content='Public answer.')]}, 'pending': False}}
    graph = Graph()
    graph.settings = settings
    logger = StructuredLogger(settings.data_dir / 'public.jsonl')
    stream = list(RagPipeline(graph, logger).run('Question', thread_id='privacy'))
    public = json.dumps(stream) + logger.log_path.read_text(encoding='utf-8')
    assert secret not in public and 'sk-private' not in public
    model = next(row['data'] for row in stream if row['event'] == 'model_call')
    assert model['details']['input_tokens'] == 3 and model['model_call_id'] == 'model-observed'
