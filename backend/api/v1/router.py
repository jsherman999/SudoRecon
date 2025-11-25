"""API v1 router aggregation."""

from fastapi import APIRouter

from .groups import router as groups_router
from .logs import router as logs_router
from .scan import router as scan_router
from .servers import router as servers_router

api_router = APIRouter()

# Include all sub-routers
api_router.include_router(servers_router, prefix="/servers", tags=["servers"])
api_router.include_router(groups_router, prefix="/groups", tags=["groups"])
api_router.include_router(scan_router, prefix="/scan", tags=["scan"])
api_router.include_router(logs_router, prefix="/logs", tags=["logs"])
