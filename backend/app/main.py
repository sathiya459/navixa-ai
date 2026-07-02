from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.config.settings import get_settings

settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="AI-Powered Multi-Cloud Network Architecture Visibility & Exposure Analytics",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request, exc):  # noqa: ARG001
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "code": "internal_error"},
        )

    @app.get("/health", tags=["Health"])
    async def health_check() -> dict:
        return {"status": "ok", "service": settings.app_name}

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
