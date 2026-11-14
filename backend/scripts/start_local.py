"""Launch the existing application with the loopback-only demo login."""

import os
from secrets import token_urlsafe
import sys
from threading import Thread

from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.auth.security import hash_password
from app.config import Settings, get_settings
from app.knowledge.embeddings import EmbeddingService


def configure_local_login(settings: Settings) -> None:
    settings.admin_username = "admin"
    settings.admin_password_hash = hash_password("123456")
    settings.jwt_secret = token_urlsafe(32)


def prepare_dense_model(settings: Settings) -> None:
    if settings.effective_embedding_backend != "fastembed":
        return
    try:
        EmbeddingService(settings).embed_one("startup")
    except RuntimeError:
        from fastembed import TextEmbedding

        print("Downloading the local Dense embedding model...", flush=True)
        model = TextEmbedding(
            model_name=settings.embedding_model,
            cache_dir=str(settings.embedding_cache_path),
        )
        next(model.embed(["startup"]))


def main(*, parent_pipe: bool = False) -> int:
    settings = get_settings()
    if settings.llm_provider == "openai_compatible":
        missing = [
            key.upper() for key in ("llm_base_url", "llm_api_key", "llm_model")
            if not getattr(settings, key).strip()
        ]
        if missing:
            print(f"Set {', '.join(missing)} in backend/.env.", file=sys.stderr)
            return 1
    try:
        prepare_dense_model(settings)
    except Exception as exc:
        print(f"Could not prepare the local embedding model ({type(exc).__name__}).", file=sys.stderr)
        return 1

    # app.main uses this same cached Settings instance when it creates the app.
    configure_local_login(settings)
    import uvicorn
    from app.main import app

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8000, proxy_headers=False))
    if parent_pipe:
        # On Windows the venv executable can be a redirector. EOF reaches the
        # Uvicorn process itself even when it is not the launcher's direct child.
        def stop_on_parent_exit() -> None:
            os.read(sys.stdin.fileno(), 1)
            server.should_exit = True

        Thread(target=stop_on_parent_exit, daemon=True).start()
    server.run()
    return 0 if server.started else 1


if __name__ == "__main__":
    raise SystemExit(main(parent_pipe="--parent-pipe" in sys.argv[1:]))
