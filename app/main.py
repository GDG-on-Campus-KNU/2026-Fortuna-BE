from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings
from app.core.deps import get_static_audio_dir
from app.core.errors import register_exception_handlers



@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    from app.core.database import Base, engine
    from app.models.user import User as _User  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield
    finally:
        await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    settings.validate_runtime_settings()
    application = FastAPI(
        title="Fortuna API",
        description="2026 Fortuna Backend API",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(application)
    application.include_router(api_router, prefix="/api/v1")

    audio_dir = get_static_audio_dir()
    if audio_dir is not None:
        application.mount(
            "/static/audio",
            StaticFiles(directory=audio_dir),
            name="audio",
        )

    return application


app = create_app()
