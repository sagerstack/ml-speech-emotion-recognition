"""
v2 API router (Clean Architecture).

This module provides the v2 API router that uses clean architecture principles.
"""

from fastapi import APIRouter

from app.api.v2.endpoints import inference

api_v2_router = APIRouter()

# Include endpoint routers
api_v2_router.include_router(
    inference.router, prefix="/inference", tags=["inference-v2"]
)
