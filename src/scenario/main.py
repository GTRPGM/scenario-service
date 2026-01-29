# src/scenario/main.py

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, status

from scenario.api.v1.api import api_router
from scenario.core.config import settings
from scenario.core.deps import db_handler
from scenario.infra.db.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manages application startup and shutdown.
    Attempts to connect and initialize the database.
    """
    try:
        # Connect to database
        await db_handler.connect()
        print("[+] Database connected.")

        # Initialize tables and graphs (Idempotent)
        await init_db(db_handler)
    except Exception as e:
        print(f"[!] Database initialization failed: {e}")
        print("[*] Service will continue, but DB-dependent endpoints may fail.")

    yield

    # Cleanup on shutdown
    await db_handler.close()
    print("[-] Database connection closed.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# Root endpoint for quick check
@app.get("/", tags=["system"])
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}", "docs": "/docs"}


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
