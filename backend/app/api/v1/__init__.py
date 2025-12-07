"""API v1 router configuration.

V1 API provides monitoring endpoints only.
Inference endpoints are available in v2.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import monitoring

api_router = APIRouter()
api_router.include_router(monitoring.router, tags=["monitoring"])
