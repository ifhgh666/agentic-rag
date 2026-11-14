"""Load fixed upstream business code in its own module namespace for parity tests."""
import ast
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
import sys
from types import ModuleType

import tiktoken

ROOT = Path(__file__).resolve().parents[1] / 'fixtures/reference016/upstream/project'


@contextmanager
def baseline_graph():
    prefix = '_reference016_baseline'
    names = []
    package = ModuleType(prefix)
    package.__path__ = []
    sys.modules[prefix] = package
    names.append(prefix)
    def load(name, source):
        module = ModuleType(prefix + '.' + name)
        module.__package__ = prefix
        module.__file__ = str(ROOT / (name + '.py'))
        sys.modules[module.__name__] = module
        names.append(module.__name__)
        exec(compile(source, module.__file__, 'exec'), module.__dict__)
        return module
    try:
        load('config', (ROOT / 'config.py').read_text(encoding='utf-8'))
        utility_source = (ROOT / 'utils.py').read_text(encoding='utf-8')
        functions = [node for node in ast.parse(utility_source).body
                     if isinstance(node, ast.FunctionDef) and node.name in {'_get_token_encoding', 'estimate_context_tokens'}]
        utility = load('utils', 'from functools import lru_cache\nimport tiktoken\n' +
                       '\n\n'.join(ast.get_source_segment(utility_source, node) for node in functions))
        for name in ['graph_state', 'schemas', 'prompts', 'nodes', 'edges', 'graph']:
            source = (ROOT / 'rag_agent' / (name + '.py')).read_text(encoding='utf-8')
            source = source.replace('from config import ', 'from .config import ')
            source = source.replace('from utils import ', 'from .utils import ')
            source = source.replace('from core.execution_logger import log_route', 'def log_route(*args): pass')
            source = source.replace('from core.execution_logger import logged_node', 'def logged_node(name, node): return node')
            module = load(name, source)
        yield module.create_agent_graph
    finally:
        for name in reversed(names):
            sys.modules.pop(name, None)
