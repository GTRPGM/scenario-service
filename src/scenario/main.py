# src/scenario/main.py

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, status

from scenario.api.v1.api import api_router
from scenario.core.config import settings
from scenario.core.deps import db_handler
from scenario.infra.db.init_db import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
# Ensure logs are visible in uvicorn
logging.getLogger("uvicorn").propagate = True
logger = logging.getLogger("scenario")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manages application startup and shutdown.
    Attempts to connect and initialize the database.
    """
    try:
        # Connect to database
        await db_handler.connect()
        logger.info("Database connected.")

        # Initialize tables and graphs (Idempotent)
        await init_db(db_handler)
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        logger.warning("Service will continue, but DB-dependent endpoints may fail.")

    yield

    # Cleanup on shutdown
    await db_handler.close()
    logger.info("Database connection closed.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# Root endpoint for quick check
@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}", "docs": "/docs"}


# Basic health check for the service itself
@app.get("/health", status_code=status.HTTP_200_OK, tags=["system"])
async def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "database": "connected" if db_handler.pool else "disconnected",
    }


# API routes
app.include_router(api_router, prefix="/api/v1")
