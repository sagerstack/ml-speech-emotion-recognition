"""Run inference use case."""

import time
from typing import Any

from app.domain.model.entities.inference import Inference
from app.domain.model.entities.raw_audio import RawAudio
from app.domain.model.exceptions.prediction_failed_error import PredictionFailedError
from app.domain.model.repositories.model_repository import ModelRepository
from app.domain.model.services.audio_processor import AudioProcessor
from app.domain.model.value_objects.emotion import Emotion
from app.domain.model.value_objects.model_version import ModelVersion


class RunInferenceUseCase:
    """Use case for running emotion inference on audio.

    This use case orchestrates the complete inference workflow:
    1. Validate audio input
    2. Extract features from audio
    3. Load ML model
    4. Run prediction
    5. Create inference result
    6. Optionally log to monitoring service

    This follows clean architecture:
    - Depends on domain abstractions (AudioProcessor, ModelRepository)
    - Implements business logic (inference workflow)
    - Returns domain entities (Inference)
    """

    def __init__(
        self,
        audio_processor: AudioProcessor,
        model_repository: ModelRepository,
        logger: Any,
        log_prediction_use_case: Any = None,
    ):
        """Initialize RunInferenceUseCase.

        Args:
            audio_processor: Audio processing service
            model_repository: Model repository for loading models
            logger: Structlog logger instance for structured logging (accepts **kwargs)
            log_prediction_use_case: Optional use case for logging predictions to monitoring
        """
        self.audio_processor = audio_processor
        self.model_repository = model_repository
        self.logger = logger
        self.log_prediction_use_case = log_prediction_use_case

    def execute(
        self,
        audio_bytes: bytes,
        filename: str,
        model_version: str = "v4",
        audio_features: bool = False,
        enable_monitoring: bool = False,
        api_version: str = "v1",
    ) -> Inference:
        """Execute inference on audio.

        Args:
            audio_bytes: Raw audio file bytes
            filename: Original filename
            model_version: Model version to use (default: "v4")
            audio_features: Include audio features data in result (default: False)
            enable_monitoring: Log prediction to monitoring service (default: False)
            api_version: API endpoint version for monitoring (default: "v1")

        Returns:
            Inference result with predicted emotion and probabilities

        Raises:
            InvalidAudioError: If audio is invalid or cannot be processed
            ModelNotFoundError: If requested model version doesn't exist
            PredictionFailedError: If prediction fails
        """
        start_time = time.time()

        self.logger.info(
            "Starting inference",
            filename=filename,
            model_version=model_version,
            audio_size_bytes=len(audio_bytes),
            audio_features_requested=audio_features,
        )

        try:
            # Step 1: Create RawAudio entity
            raw_audio = RawAudio.from_bytes(audio_bytes, filename)

            # Step 2: Validate audio
            self.audio_processor.validate_audio(raw_audio)

            # Step 3: Extract features (with or without audio_features)
            audio_features_data = None
            if audio_features:
                # Extract both model features AND audio_features data
                result = self.audio_processor.extract_features_with_audio_data(raw_audio)
                features = result["features"]
                audio_features_data = result["audio_features"]
            else:
                # Extract only model features
                features = self.audio_processor.extract_features(raw_audio)

            # Step 4: Load model (returns EmotionModel interface, not raw pickle)
            version = ModelVersion.from_string(model_version)
            emotion_model = self.model_repository.load_model(version)

            # Step 5: Run prediction using domain interface
            # EmotionModel handles all the complexity:
            # - Reshaping features (1D -> 2D)
            # - Calling underlying model
            # - Extracting single sample probabilities
            # - Mapping to Emotion enum
            # - Validating output
            all_probabilities = emotion_model.predict_emotion_probabilities(features)

            # Step 6: Find predicted emotion (highest probability)
            predicted_emotion = max(all_probabilities.items(), key=lambda x: x[1])[0]

            # Step 7: Calculate processing time
            end_time = time.time()
            processing_time_ms = (end_time - start_time) * 1000

            # Step 8: Optionally log to monitoring service
            prediction_id = None
            if enable_monitoring and self.log_prediction_use_case:
                prediction_id = self.log_prediction_use_case.execute(
                    emotion=predicted_emotion,
                    confidence=all_probabilities[predicted_emotion],
                    probabilities=all_probabilities,
                    features={f"feature_{i}": float(f) for i, f in enumerate(features)},
                    audio_bytes=audio_bytes,
                    filename=filename,
                    model_version=model_version,
                    api_version=api_version,
                )

            # Step 9: Create and return Inference entity
            inference = Inference.create(
                emotion=predicted_emotion,
                all_probabilities=all_probabilities,
                model_version=version,
                processing_time_ms=processing_time_ms,
                audio_features=audio_features_data,
                prediction_id=prediction_id,
            )

            self.logger.info(
                "Inference completed successfully",
                filename=filename,
                model_version=model_version,
                predicted_emotion=str(predicted_emotion),
                confidence=all_probabilities[predicted_emotion],
                processing_time_ms=round(processing_time_ms, 2),
                includes_audio_features=audio_features_data is not None,
                monitoring_enabled=enable_monitoring,
                prediction_id=prediction_id,
            )

            return inference

        except (IndexError, KeyError) as e:
            self.logger.error(
                "Inference failed",
                filename=filename,
                model_version=model_version,
                error=str(e),
            )
            raise PredictionFailedError(f"Failed to process model predictions: {str(e)}")
        except Exception as e:
            self.logger.error(
                "Inference failed with unexpected error",
                filename=filename,
                model_version=model_version,
                error=str(e),
            )
            raise
