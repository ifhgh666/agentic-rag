from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import auth, chat, debug, errors, knowledge, logs
from .auth.service import AuthService
from .config import Settings, get_settings
from .knowledge.manager import DocumentManager
from .knowledge.pdf_parser import PdfParser
from .knowledge.stores import DocumentStore
from .observability.logger import StructuredLogger
from .rag.context_builder import ContextBuilder
from .rag.conversation_memory import ConversationMemory
from .rag.embeddings import EmbeddingService
from .rag.evaluator import AnswerEvaluator
from .rag.generator import AnswerGenerator
from .rag.graph import AgentGraphService
from .rag.index_store import IndexStore
from .rag.pipeline import RagPipeline
from .rag.retriever import Retriever
from .schemas.common import HealthResponse


@dataclass
class Services:
    settings: Settings
    logger: StructuredLogger
    auth: AuthService
    documents: DocumentStore
    index: IndexStore
    document_manager: DocumentManager
    retriever: Retriever
    pipeline: RagPipeline


def build_services(settings: Settings) -> Services:
    settings.ensure_data_dirs()
    logger = StructuredLogger(
        settings.data_dir / "logs" / "app.jsonl",
        enabled=settings.execution_logging_enabled,
        max_chars=settings.execution_log_max_chars,
    )
    documents = DocumentStore(settings.data_dir)
    embedder = EmbeddingService(settings)
    index = IndexStore(settings.data_dir, embedder, document_store=documents)
    retriever = Retriever(settings, index, documents)
    context_builder = ContextBuilder(settings, documents)
    document_manager = DocumentManager(settings, documents, PdfParser(), index, logger)
    # Graph 与直连路径共用同一提供商实例，避免重复创建本地模型客户端。
    generator = AnswerGenerator(settings)
    pipeline = RagPipeline(
        retriever,
        context_builder,
        generator,
        AnswerEvaluator(),
        logger,
        graph_service=AgentGraphService(
            settings=settings,
            retriever=retriever,
            context_builder=context_builder,
            generator=generator,
            evaluator=AnswerEvaluator(),
            document_store=documents,
            memory=ConversationMemory(settings.main_history_messages_to_keep),
        ),
    )
    return Services(
        settings=settings,
        logger=logger,
        auth=AuthService(settings),
        documents=documents,
        index=index,
        document_manager=document_manager,
        retriever=retriever,
        pipeline=pipeline,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="PDF RAG 知识库问答", version="1.0.0")
    app.state.services = build_services(settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    errors.install_error_handlers(app)

    @app.get("/api/health", response_model=HealthResponse, tags=["健康检查"])
    def health():
        services: Services = app.state.services
        return HealthResponse(status="ok", service="pdf-rag-api", index_ready=services.index.ready)

    app.include_router(auth.router, prefix="/api")
    app.include_router(knowledge.router, prefix="/api")
    app.include_router(debug.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")
    app.include_router(logs.router, prefix="/api")
    return app


app = create_app()
