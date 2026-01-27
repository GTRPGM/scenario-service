# src/scenario/main.py

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, status

from scenario.api.v1.api import api_router
from scenario.core.config import settings
from scenario.core.deps import db_handler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages application startup and shutdown."""
    await db_handler.connect()
    yield
    await db_handler.close()


app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", status_code=status.HTTP_200_OK, tags=["system"])
async def health_check() -> dict[str, str]:
    """Self health check endpoint for the scenario service."""
    return {"status": "healthy"}
