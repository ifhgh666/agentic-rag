from dataclasses import dataclass
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import auth, chat, debug, errors, knowledge, logs
from .auth.service import AuthService
from .config import Settings, get_settings
from .knowledge.manager import DocumentManager
from .knowledge.pdf_parser import PdfParser
from .knowledge.stores import DocumentStore
from .observability.logger import StructuredLogger
from .observability.diagnostics import DiagnosticRecorder
from .core.reference_session import AgentGraphService
from .knowledge.retrieval import Retriever
from .knowledge.embeddings import EmbeddingService
from .knowledge.index import IndexStore
from .core.pipeline import RagPipeline
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
    diagnostics: DiagnosticRecorder


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
    document_manager = DocumentManager(settings, documents, PdfParser(), index, logger)
    diagnostics = DiagnosticRecorder(settings.data_dir / "logs" / "loop_traces",
                                     enabled=settings.execution_logging_enabled)
    pipeline = RagPipeline(AgentGraphService(settings, retriever, documents), logger, diagnostics)
    return Services(
        settings=settings,
        logger=logger,
        auth=AuthService(settings),
        documents=documents,
        index=index,
        document_manager=document_manager,
        retriever=retriever,
        pipeline=pipeline,
        diagnostics=diagnostics,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        application.state.services.diagnostics.start()
        try:
            yield
        finally:
            application.state.services.diagnostics.close()

    app = FastAPI(title="PDF RAG 知识库问答", version="1.0.0", lifespan=lifespan)
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
