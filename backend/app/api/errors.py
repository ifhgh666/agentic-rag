from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_error_handler(_request: Request, exc: HTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else "请求失败。"
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": detail, "message": detail}},
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(_request: Request, exc: ValueError):
        return JSONResponse(status_code=422, content={"error": {"code": "VALIDATION_ERROR", "message": str(exc)}})
