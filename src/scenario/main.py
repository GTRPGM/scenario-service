# src/scenario/main.py

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, status

from scenario.api.v1.api import api_router
from scenario.core.config import settings
from scenario.core.deps import db_handler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manages application startup and shutdown.
    Attempts to connect to the database but does not block app startup on failure.
    """
    # Attempt to connect in the background to not block Swagger/Health check
    connection_task = asyncio.create_task(db_handler.connect())

    def check_connection_result(task: asyncio.Task):
        try:
            task.result()
            print("[+] Database connected successfully.")
        except Exception as e:
            print(f"[!] Database connection deferred or failed: {e}")
            print(
                "[*] Service is up. DB-dependent "
                "endpoints will retry connection on request."
            )

    connection_task.add_done_callback(check_connection_result)

    yield

    # Cleanup on shutdown
    connection_task.cancel()
    await db_handler.close()
    print("[-] Database connection closed.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)


# Root endpoint for quick check
@app.get("/", tags=["system"])
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}", "docs": "/api/docs"}


# Self health check endpoint
@app.get("/health", status_code=status.HTTP_200_OK, tags=["system"])
async def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "database": "connected" if db_handler.pool else "disconnected",
    }


# API routes
app.include_router(api_router, prefix="/api/v1")
