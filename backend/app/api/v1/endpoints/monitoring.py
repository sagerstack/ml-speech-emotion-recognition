"""API endpoints for Evidently monitoring."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.services.evidently_monitoring import get_monitoring_service
from app.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/monitoring/summary")
async def monitoring_summary():
    """Return buffer stats and last report metadata."""

    service = get_monitoring_service()
    return service.summary()


@router.get("/monitoring/buffer/stats")
async def monitoring_buffer_stats():
    """Expose lightweight buffer statistics for the UI."""

    service = get_monitoring_service()
    return service.buffer.stats()


@router.post("/monitoring/generate")
async def monitoring_generate():
    """Trigger Evidently report generation manually."""

    service = get_monitoring_service()
    try:
        report = service.generate_report()
        return {"message": "Report generated", "report": report.to_dict()}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # pragma: no cover - runtime safety
        logger.error("Failed to generate monitoring report", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to generate monitoring report")


@router.get("/monitoring/reports")
async def monitoring_reports():
    """List generated reports."""

    service = get_monitoring_service()
    return {"reports": service.list_reports()}


@router.get("/monitoring/reports/{report_name}")
async def monitoring_report(report_name: str):
    """Serve a specific HTML report file."""

    service = get_monitoring_service()
    report_path = service.get_report_path(report_name)
    if report_path is None:
        raise HTTPException(status_code=404, detail="Report not found")

    return FileResponse(report_path)
