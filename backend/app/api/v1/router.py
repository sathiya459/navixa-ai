from fastapi import APIRouter

from app.api.v1.auth import router as auth_router

api_router = APIRouter()
api_router.include_router(auth_router)

# Module routers are registered here as they are implemented:
# feature/phase1-tenant-registry -> tenants.router
# feature/phase1-aws-collector   -> discover.router
# feature/phase1-hub-spoke-validation -> validate.router
