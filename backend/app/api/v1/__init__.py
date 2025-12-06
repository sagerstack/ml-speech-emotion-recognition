"""
API v1 router configuration (legacy).

Note: V1 inference endpoints have been decommissioned and migrated to v2.
Only monitoring endpoints remain active in v1.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import inference, monitoring

api_router = APIRouter()
# V1 inference endpoints decommissioned - router is now empty
api_router.include_router(inference.router, prefix="/inference", tags=["inference-v1-deprecated"])
# Monitoring endpoints remain active
api_router.include_router(monitoring.router, tags=["monitoring"])
