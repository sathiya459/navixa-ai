from fastapi import APIRouter

api_router = APIRouter()

# Module routers are registered here as they are implemented:
# feature/phase1-jwt-auth        -> auth.router
# feature/phase1-tenant-registry -> tenants.router
# feature/phase1-aws-collector   -> discover.router
# feature/phase1-hub-spoke-validation -> validate.router
