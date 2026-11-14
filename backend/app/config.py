from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    """应用配置。生产环境应通过 backend/.env 或进程环境变量覆盖默认值。"""

    # 使用绝对路径加载配置，避免从项目根目录或 VSCode 启动时漏读 backend/.env。
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    data_dir: Path = Path(__file__).resolve().parents[1] / "data"
    admin_username: str = "admin"
    admin_password_hash: str = ""
    jwt_secret: str = "local-development-secret-change-me"
    jwt_expire_minutes: int = 60
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_provider: Literal["ollama", "openai_compatible", "fake"] = "ollama"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = ""
    llm_temperature: float = 0.0
    llm_seed: int = 42
    llm_timeout_seconds: float = 120.0
    llm_max_output_tokens: int = 768
    max_llm_calls_per_request: int = 12
    max_simple_llm_calls: int = 8
    model_context_window: int = 4096
    model_context_safety_tokens: int = 256
    agent_loop_protocol: Literal["native", "structured"] = "native"
    request_timeout_seconds: float = Field(default=300.0, gt=0, le=300)
    max_query_analysis_calls: int = 1
    max_query_rewrite_calls: int = 1
    max_answer_calls: int = 1
    max_summary_calls: int = 1
    max_context_tokens: int = 3072
    rag_cache_ttl_seconds: int = 300
    rag_cache_max_entries: int = 256
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dimension: int = 384
    embedding_cache_dir: Path | None = None
    # 兼容 V2 的开关；V3 默认用本地 ONNX Dense，测试可显式选 deterministic。
    use_transformer_embedding: bool = True
    embedding_backend: Literal["fastembed", "deterministic"] | None = None
    qdrant_db_path: Path | None = None
    child_collection: str = "document_child_chunks"
    dense_vector_name: str = "dense"
    sparse_model: str = "Qdrant/bm25"
    sparse_model_path: Path | None = None
    sparse_offline_fallback: bool = False
    sparse_vector_name: str = "sparse"
    retrieval_top_k: int = 7
    retrieval_min_score: float = 0.4
    max_tool_calls: int = 16
    max_iterations: int = 10
    graph_recursion_limit: int = 80
    # Legacy parsing compatibility only; current Parent reads are model tool actions.
    agent_parent_threshold_chars: int = 240
    main_history_messages_to_keep: int = 4
    main_history_input_token_limit: int = 4000
    execution_logging_enabled: bool = True
    execution_log_max_chars: int = 1200
    base_token_threshold: int = 2000
    token_growth_factor: float = 0.9
    child_chunk_size: int = 500
    child_chunk_overlap: int = 100
    parent_chunk_size: int = 3000
    max_context_chars: int = 12000
    max_question_chars: int = 2000
    max_upload_bytes: int = 25 * 1024 * 1024

    def ensure_data_dirs(self) -> None:
        for name in ("documents", "index", "logs"):
            (self.data_dir / name).mkdir(parents=True, exist_ok=True)
        self.qdrant_path.mkdir(parents=True, exist_ok=True)

    @property
    def qdrant_path(self) -> Path:
        configured = self.qdrant_db_path
        if configured is None:
            return self.data_dir / "qdrant"
        return configured if configured.is_absolute() else self.data_dir / configured

    @property
    def effective_embedding_backend(self) -> str:
        if self.embedding_backend is not None:
            return self.embedding_backend
        return "fastembed" if self.use_transformer_embedding else "deterministic"

    @property
    def embedding_cache_path(self) -> Path:
        configured = self.embedding_cache_dir
        if configured is None:
            return self.data_dir / "models"
        return configured if configured.is_absolute() else self.data_dir / configured

    @property
    def origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_data_dirs()
    return settings
