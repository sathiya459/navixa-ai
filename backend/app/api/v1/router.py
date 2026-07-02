from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.discover import router as discover_router
from app.api.v1.graph import router as graph_router
from app.api.v1.insightai import router as insightai_router
from app.api.v1.pathfinder import router as pathfinder_router
from app.api.v1.reports import router as reports_router
from app.api.v1.tenants import router as tenants_router
from app.api.v1.validate import router as validate_router
from app.api.v1.watch import router as watch_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(tenants_router)
api_router.include_router(discover_router)
api_router.include_router(graph_router)
api_router.include_router(validate_router)
api_router.include_router(pathfinder_router)
api_router.include_router(insightai_router)
api_router.include_router(reports_router)
api_router.include_router(watch_router)
