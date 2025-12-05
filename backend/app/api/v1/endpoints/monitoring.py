"""API endpoints for Evidently monitoring."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.services.evidently_monitoring import get_monitoring_service
from app.services.prediction_buffer import get_prediction_buffer
from app.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


class FeedbackRequest(BaseModel):
    """Request body for user feedback on predictions."""

    actual_emotion: str = Field(
        ...,
        description="The actual emotion label provided by the user",
        pattern="^(angry|disgust|fear|happy|neutral|sad)$",
    )


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


@router.post("/monitoring/feedback/{prediction_id}")
async def submit_feedback(prediction_id: str, request: FeedbackRequest):
    """Submit user feedback (ground truth) for a prediction.

    This enables concept drift and label drift monitoring by providing
    the actual emotion labels for predictions.

    Args:
        prediction_id: UUID of the prediction to update
        request: Feedback request containing actual_emotion

    Returns:
        Success message with prediction details
    """

    buffer = get_prediction_buffer()
    success = buffer.update_feedback(prediction_id, request.actual_emotion)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Prediction with ID {prediction_id} not found in buffer. "
            "It may have been evicted (buffer holds most recent 500 predictions).",
        )

    logger.info(
        "Feedback submitted successfully",
        prediction_id=prediction_id,
        actual_emotion=request.actual_emotion,
    )

    return {
        "message": "Feedback submitted successfully",
        "prediction_id": prediction_id,
        "actual_emotion": request.actual_emotion,
    }
