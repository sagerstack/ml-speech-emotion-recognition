"""
API v1 router configuration.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import inference, inference_local, monitoring

api_router = APIRouter()
api_router.include_router(inference.router, prefix="/infer", tags=["inference"])
api_router.include_router(inference_local.router, tags=["local-models"])
api_router.include_router(monitoring.router, tags=["monitoring"])