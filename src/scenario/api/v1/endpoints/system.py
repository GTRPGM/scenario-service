from typing import Dict

import httpx
from fastapi import APIRouter, status

from scenario.core.config import settings
from scenario.core.deps import db_handler

router = APIRouter()


@router.get("/services/health", status_code=status.HTTP_200_OK)
async def services_health_check() -> Dict[str, str]:
    """
    Check the health of external dependent services.
    """
    results = {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "database": "connected" if db_handler.pool else "disconnected",
    }

    # External services to check
    services = {
        "llm_gateway": settings.LLM_GATEWAY_URL,
        "state_manager": settings.STATE_MANAGER_URL,
        "rule_engine": settings.RULE_ENGINE_URL,
    }

    async with httpx.AsyncClient(timeout=1.0) as client:
        for name, url in services.items():
            try:
                # Most services should have a /health endpoint
                response = await client.get(f"{url}/health")
                if response.status_code == 200:
                    results[name] = "up"
                else:
                    results[name] = f"down (status: {response.status_code})"
                    results["status"] = "degraded"
            except Exception:
                results[name] = "unreachable"
                results["status"] = "degraded"

    return results


@router.get("/version", status_code=status.HTTP_200_OK)
async def get_version() -> Dict[str, str]:
    return {"version": settings.VERSION}
