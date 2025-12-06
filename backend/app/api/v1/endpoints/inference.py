"""
V1 Inference API endpoints - DECOMMISSIONED.

All inference endpoints have been migrated to v2 API with clean architecture support.
This file is kept for reference but all inference endpoints have been removed.

Migration mapping:
- POST /v1/inference/latest → POST /v2/inference
- POST /v1/inference/{version} → POST /v2/inference (deprecated)
- POST /v1/inference/all → Removed (use frontend comparison with v2)
- GET /v1/inference/versions → GET /v2/inference/versions
- GET /v1/inference/{version}/info → GET /v2/inference/{version}/info
- GET /v1/inference/latest/info → GET /v2/inference/info

Use /v2/inference endpoints for all inference operations.

Note: The monitoring endpoints remain active in /v1/monitoring
"""

from fastapi import APIRouter

# Empty router - all endpoints decommissioned
router = APIRouter()
