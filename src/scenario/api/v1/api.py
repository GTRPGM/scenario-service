from fastapi import APIRouter

from scenario.api.v1.endpoints import check, generation, manage, system

api_router = APIRouter()
api_router.include_router(system.router, prefix="/system", tags=["System"])
api_router.include_router(generation.router, prefix="/generation", tags=["Generation"])
api_router.include_router(check.router, prefix="/check", tags=["Check"])
api_router.include_router(manage.router, prefix="/manage", tags=["Manage"])
