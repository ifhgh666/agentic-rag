"""Reference-compatible tools and token estimation; no evidence-admission policy."""
from functools import lru_cache
from uuid import UUID

from langchain_core.tools import StructuredTool
import tiktoken

from ..schemas.documents import DocumentStatus
from .graph_state import CHILD_CHUNK_SEPARATOR


@lru_cache(maxsize=1)
def _get_token_encoding():
    try:
        return tiktoken.encoding_for_model("gpt-4")
    except Exception:
        try:
            return tiktoken.get_encoding("cl100k_base")
        except Exception:
            return None


def estimate_context_tokens(messages: list) -> int:
    contents = [str(msg.content) for msg in messages if hasattr(msg, "content") and msg.content]
    encoding = _get_token_encoding()
    if encoding is None:
        return sum(max(1, len(content) // 4) for content in contents)
    return sum(len(encoding.encode(content)) for content in contents)


def create_rag_tools(retriever, document_store, settings):
    def search_child_chunks(query: str, limit: int = 7):
        """Search document excerpts for evidence related to the user question.

        Use this as the first retrieval step. Results include parent IDs, file
        names, and short child-chunk excerpts. If excerpts are relevant but too
        fragmented to answer confidently, call retrieve_parent_chunks with the
        returned parent_id.

        Args:
            query: Focused search query with concrete keywords from the question.
            limit: Maximum number of child chunks to return.
        """
        try:
            if not str(query).strip() or not 1 <= limit <= 20:
                raise ValueError("INVALID_QUERY")
            if not retriever.index_store.ready:
                raise ValueError("INDEX_NOT_READY")
            results = retriever.search(query, top_k=limit, min_score=settings.retrieval_min_score)
            records = [item.model_dump(mode="json") for item in results]
            if not records:
                return "NO_RELEVANT_CHUNKS", {"tool": "search_child_chunks", "query": query, "results": []}
            text = CHILD_CHUNK_SEPARATOR.join(
                f"Parent ID: {item['parent_id']}\nFile Name: {item['filename']}\nContent: {(item.get('text') or item['content_preview']).strip()}"
                for item in records
            )
            return text, {"tool": "search_child_chunks", "query": query, "results": records}
        except Exception as exc:
            # The original error channel is retained; private exception bodies are not.
            code = str(exc) if str(exc) in {"INDEX_NOT_READY", "INVALID_QUERY"} else type(exc).__name__
            return "RETRIEVAL_ERROR: " + code, {"tool": "search_child_chunks", "error": code, "results": []}

    def retrieve_parent_chunks(parent_id: str):
        """Retrieve the full parent chunk for a relevant child search result.

        Use this only after search_child_chunks returns a relevant parent_id and
        the child excerpt needs more surrounding context. Do not call this for
        parent IDs already available in compressed context.

        Args:
            parent_id: Parent chunk ID returned by search_child_chunks.
        """
        try:
            parent = document_store.get_parent(UUID(parent_id))
            if parent is None:
                return "NO_PARENT_DOCUMENT", {"tool": "retrieve_parent_chunks"}
            document = document_store.get_document(parent.document_id)
            if document is None or document.status != DocumentStatus.ready:
                return "NO_PARENT_DOCUMENT", {"tool": "retrieve_parent_chunks"}
            record = {"parent_id": str(parent.parent_id), "document_id": str(parent.document_id),
                      "filename": document.filename, "section_title": parent.section_title,
                      "page_start": parent.page_start, "page_end": parent.page_end, "text": parent.text}
            return (f"Parent ID: {parent.parent_id}\nFile Name: {document.filename}\nContent: {parent.text.strip()}",
                    {"tool": "retrieve_parent_chunks", "parent": record})
        except Exception as exc:
            return "PARENT_RETRIEVAL_ERROR: " + type(exc).__name__, {"tool": "retrieve_parent_chunks", "error": type(exc).__name__}

    return [
        StructuredTool.from_function(search_child_chunks, response_format="content_and_artifact"),
        StructuredTool.from_function(retrieve_parent_chunks, response_format="content_and_artifact"),
    ]
