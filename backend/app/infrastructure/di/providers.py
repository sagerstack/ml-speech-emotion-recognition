"""FastAPI dependency providers for clean architecture.

This module provides FastAPI Depends() functions that wire together
the application's dependencies. These providers integrate with FastAPI's
dependency injection system.

The providers follow clean architecture:
- Return domain abstractions (AudioProcessor, ModelRepository, Use Cases)
- Hide implementation details from endpoints
- Enable easy testing through dependency override
"""

from fastapi import Depends

from app.domain.model.repositories.model_repository import ModelRepository
from app.domain.model.services.audio_processor import AudioProcessor
from app.infrastructure.di.container import get_container
from app.infrastructure.monitoring.evidently_service import get_monitoring_service, EvidentlyService
from app.infrastructure.observability.logging import get_logger
from app.use_cases.model.get_model_info import GetModelInfoUseCase
from app.use_cases.model.get_model_versions import GetModelVersionsUseCase
from app.use_cases.model.list_models import ListModelsUseCase
from app.use_cases.model.run_inference import RunInferenceUseCase
from app.use_cases.monitoring.log_prediction_for_monitoring import LogPredictionForMonitoringUseCase


def get_audio_processor() -> AudioProcessor:
    """FastAPI dependency for AudioProcessor.

    Returns:
        AudioProcessor instance from DI container
    """
    container = get_container()
    return container.get_audio_processor()


def get_model_repository() -> ModelRepository:
    """FastAPI dependency for ModelRepository.

    Returns:
        ModelRepository instance from DI container
    """
    container = get_container()
    return container.get_model_repository()


def get_log_prediction_for_monitoring_use_case(
    monitoring_service: EvidentlyService = Depends(get_monitoring_service),
) -> LogPredictionForMonitoringUseCase:
    """FastAPI dependency for LogPredictionForMonitoringUseCase.

    Args:
        monitoring_service: Injected Evidently monitoring service

    Returns:
        LogPredictionForMonitoringUseCase with dependencies
    """
    logger = get_logger("app.use_cases.monitoring.log_prediction_for_monitoring")
    return LogPredictionForMonitoringUseCase(
        monitoring_service=monitoring_service,
        logger=logger,
    )


def get_run_inference_use_case(
    audio_processor: AudioProcessor = Depends(get_audio_processor),
    model_repository: ModelRepository = Depends(get_model_repository),
    log_prediction_use_case: LogPredictionForMonitoringUseCase = Depends(get_log_prediction_for_monitoring_use_case),
) -> RunInferenceUseCase:
    """FastAPI dependency for RunInferenceUseCase.

    Args:
        audio_processor: Injected audio processor
        model_repository: Injected model repository
        log_prediction_use_case: Injected monitoring log prediction use case

    Returns:
        RunInferenceUseCase with dependencies
    """
    logger = get_logger("app.use_cases.model.run_inference")
    return RunInferenceUseCase(
        audio_processor=audio_processor,
        model_repository=model_repository,
        logger=logger,
        log_prediction_use_case=log_prediction_use_case,
    )


def get_model_info_use_case(
    model_repository: ModelRepository = Depends(get_model_repository),
) -> GetModelInfoUseCase:
    """FastAPI dependency for GetModelInfoUseCase.

    Args:
        model_repository: Injected model repository

    Returns:
        GetModelInfoUseCase with dependencies
    """
    return GetModelInfoUseCase(model_repository=model_repository)


def get_list_models_use_case(
    model_repository: ModelRepository = Depends(get_model_repository),
) -> ListModelsUseCase:
    """FastAPI dependency for ListModelsUseCase.

    Args:
        model_repository: Injected model repository

    Returns:
        ListModelsUseCase with dependencies
    """
    return ListModelsUseCase(model_repository=model_repository)


def get_model_versions_use_case(
    model_repository: ModelRepository = Depends(get_model_repository),
) -> GetModelVersionsUseCase:
    """FastAPI dependency for GetModelVersionsUseCase.

    Args:
        model_repository: Injected model repository

    Returns:
        GetModelVersionsUseCase with dependencies
    """
    return GetModelVersionsUseCase(model_repository=model_repository)
