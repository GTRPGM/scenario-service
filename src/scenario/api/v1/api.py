from fastapi import APIRouter

from scenario.api.v1.endpoints import scenario

api_router = APIRouter()
api_router.include_router(scenario.router, prefix="/scenario", tags=["scenario"])
