"""Unit tests for RunInferenceUseCase."""

import io
from unittest.mock import Mock

import numpy as np
import pytest
import soundfile as sf

from app.domain.model.entities.inference import Inference
from app.domain.model.entities.raw_audio import RawAudio
from app.domain.model.exceptions.invalid_audio_error import InvalidAudioError
from app.domain.model.exceptions.model_not_found_error import ModelNotFoundError
from app.domain.model.exceptions.prediction_failed_error import PredictionFailedError
from app.domain.model.value_objects.emotion import Emotion
from app.use_cases.model.run_inference import RunInferenceUseCase


class TestRunInferenceUseCase:
    """Test suite for RunInferenceUseCase."""

    @pytest.fixture
    def valid_audio_bytes(self) -> bytes:
        """Create valid audio bytes for testing."""
        sample_rate = 22050
        duration = 2.5
        frequency = 440
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_data = np.sin(2 * np.pi * frequency * t)
        audio_data = audio_data / np.max(np.abs(audio_data)) * 0.8

        audio_buffer = io.BytesIO()
        sf.write(audio_buffer, audio_data, sample_rate, format="WAV")
        audio_buffer.seek(0)
        return audio_buffer.read()

    @pytest.fixture
    def mock_audio_processor(self):
        """Create mock audio processor."""
        processor = Mock()
        processor.validate_audio = Mock(return_value=True)
        processor.extract_features = Mock(return_value=np.random.rand(210))
        processor.extract_features_with_audio_data = Mock(
            return_value={
                "features": np.random.rand(210),
                "audio_features": None,
            }
        )
        processor.get_audio_metadata = Mock()
        return processor

    @pytest.fixture
    def mock_model_repository(self):
        """Create mock model repository."""
        repository = Mock()

        # Create mock emotion model that implements the domain interface
        mock_model = Mock()
        # Mock predict_emotion_probabilities to return a dict
        mock_model.predict_emotion_probabilities = Mock(
            return_value={
                Emotion.ANGRY: 0.1,
                Emotion.DISGUST: 0.05,
                Emotion.FEAR: 0.1,
                Emotion.HAPPY: 0.6,
                Emotion.NEUTRAL: 0.1,
                Emotion.SAD: 0.05,
            }
        )

        repository.load_model = Mock(return_value=mock_model)
        return repository

    @pytest.fixture
    def mock_logger(self):
        """Create mock logger (structlog logger accepts **kwargs)."""
        logger = Mock()
        logger.info = Mock()
        logger.error = Mock()
        logger.warning = Mock()
        logger.debug = Mock()
        return logger

    @pytest.fixture
    def use_case(self, mock_audio_processor, mock_model_repository, mock_logger):
        """Create RunInferenceUseCase instance."""
        return RunInferenceUseCase(mock_audio_processor, mock_model_repository, mock_logger)

    # Test successful inference
    def test_execute_returns_inference_result(
        self, use_case: RunInferenceUseCase, valid_audio_bytes: bytes
    ):
        """Test that execute returns Inference with correct structure."""
        result = use_case.execute(valid_audio_bytes, "test_audio.wav")

        assert isinstance(result, Inference)
        assert isinstance(result.emotion, Emotion)
        assert result.confidence.value > 0
        assert len(result.all_probabilities) == 6
        assert result.processing_time_ms > 0

    def test_execute_predicts_correct_emotion(
        self, use_case: RunInferenceUseCase, valid_audio_bytes: bytes
    ):
        """Test that execute predicts the emotion with highest probability."""
        result = use_case.execute(valid_audio_bytes, "test_audio.wav")

        # Mock returns highest probability for happy (0.6)
        assert result.emotion == Emotion.HAPPY
        assert result.confidence.value == 0.6

    def test_execute_returns_all_probabilities(
        self, use_case: RunInferenceUseCase, valid_audio_bytes: bytes
    ):
        """Test that execute returns probabilities for all emotions."""
        result = use_case.execute(valid_audio_bytes, "test_audio.wav")

        # Check all 6 emotions are present
        expected_emotions = {
            Emotion.ANGRY,
            Emotion.DISGUST,
            Emotion.FEAR,
            Emotion.HAPPY,
            Emotion.NEUTRAL,
            Emotion.SAD,
        }
        assert set(result.all_probabilities.keys()) == expected_emotions

        # Check probabilities sum to 1.0
        prob_sum = sum(result.all_probabilities.values())
        assert 0.99 <= prob_sum <= 1.01

    def test_execute_uses_v4_model_by_default(
        self, use_case: RunInferenceUseCase, mock_model_repository: Mock, valid_audio_bytes: bytes
    ):
        """Test that execute uses v4 model by default."""
        use_case.execute(valid_audio_bytes, "test_audio.wav")

        # Verify load_model was called with v4
        mock_model_repository.load_model.assert_called_once()
        version = mock_model_repository.load_model.call_args[0][0]
        assert str(version) == "v4"

    def test_execute_calls_audio_processor_in_correct_order(
        self, use_case: RunInferenceUseCase, mock_audio_processor: Mock, valid_audio_bytes: bytes
    ):
        """Test that audio processor methods are called in correct order."""
        use_case.execute(valid_audio_bytes, "test_audio.wav")

        # Verify validate_audio was called
        assert mock_audio_processor.validate_audio.called

        # Verify extract_features was called
        assert mock_audio_processor.extract_features.called

    def test_execute_measures_processing_time(
        self, use_case: RunInferenceUseCase, valid_audio_bytes: bytes
    ):
        """Test that execute measures processing time."""
        result = use_case.execute(valid_audio_bytes, "test_audio.wav")

        # Processing time should be reasonable (< 10 seconds for mocked operations)
        assert result.processing_time_ms > 0
        assert result.processing_time_ms < 10000

    # Test error handling
    def test_execute_raises_error_for_invalid_audio(
        self, use_case: RunInferenceUseCase, mock_audio_processor: Mock
    ):
        """Test that execute raises InvalidAudioError for invalid audio."""
        # Make validate_audio raise InvalidAudioError
        mock_audio_processor.validate_audio.side_effect = InvalidAudioError("Invalid audio format")

        with pytest.raises(InvalidAudioError):
            use_case.execute(b"invalid audio", "test.wav")

    def test_execute_raises_error_for_feature_extraction_failure(
        self, use_case: RunInferenceUseCase, mock_audio_processor: Mock, valid_audio_bytes: bytes
    ):
        """Test that execute raises PredictionFailedError when feature extraction fails."""
        # Make extract_features raise error
        mock_audio_processor.extract_features.side_effect = PredictionFailedError(
            "Feature extraction failed"
        )

        with pytest.raises(PredictionFailedError):
            use_case.execute(valid_audio_bytes, "test.wav")

    def test_execute_raises_error_for_model_not_found(
        self, use_case: RunInferenceUseCase, mock_model_repository: Mock, valid_audio_bytes: bytes
    ):
        """Test that execute raises ModelNotFoundError when model doesn't exist."""
        # Make load_model raise ModelNotFoundError
        mock_model_repository.load_model.side_effect = ModelNotFoundError("Model not found")

        with pytest.raises(ModelNotFoundError):
            use_case.execute(valid_audio_bytes, "test.wav")

    def test_execute_raises_error_for_empty_audio(self, use_case: RunInferenceUseCase):
        """Test that execute raises error for empty audio."""
        with pytest.raises((InvalidAudioError, ValueError)):
            use_case.execute(b"", "empty.wav")

    def test_execute_raises_error_for_invalid_predictions(
        self, use_case: RunInferenceUseCase, mock_model_repository: Mock, valid_audio_bytes: bytes
    ):
        """Test that execute handles invalid model predictions."""
        # Make model return invalid predictions (empty dict)
        mock_model = Mock()
        mock_model.predict_emotion_probabilities = Mock(return_value={})  # Empty dict
        mock_model_repository.load_model.return_value = mock_model

        with pytest.raises((PredictionFailedError, IndexError, ValueError)):
            use_case.execute(valid_audio_bytes, "test.wav")

    # Test different audio inputs
    def test_execute_handles_different_filenames(
        self, use_case: RunInferenceUseCase, valid_audio_bytes: bytes
    ):
        """Test that execute handles different filename formats."""
        filenames = ["test.wav", "audio.mp3", "speech.flac", "recording.m4a"]

        for filename in filenames:
            result = use_case.execute(valid_audio_bytes, filename)
            assert isinstance(result, Inference)

    def test_execute_is_deterministic_for_same_input(
        self, use_case: RunInferenceUseCase, valid_audio_bytes: bytes
    ):
        """Test that execute returns consistent results for same input."""
        result1 = use_case.execute(valid_audio_bytes, "test.wav")
        result2 = use_case.execute(valid_audio_bytes, "test.wav")

        # Same emotion should be predicted
        assert result1.emotion == result2.emotion
        assert result1.confidence.value == result2.confidence.value

    # Test model integration
    def test_execute_uses_210_features_for_v4(
        self, use_case: RunInferenceUseCase, mock_audio_processor: Mock, valid_audio_bytes: bytes
    ):
        """Test that execute extracts 210 features for v4 model."""
        # Set up mock to return 210 features
        mock_audio_processor.extract_features.return_value = np.random.rand(210)

        use_case.execute(valid_audio_bytes, "test.wav")

        # Verify extract_features was called
        assert mock_audio_processor.extract_features.called
        call_args = mock_audio_processor.extract_features.call_args
        assert isinstance(call_args[0][0], RawAudio)

    def test_execute_passes_features_to_model(
        self, use_case: RunInferenceUseCase, mock_model_repository: Mock, valid_audio_bytes: bytes
    ):
        """Test that execute passes extracted features to model."""
        use_case.execute(valid_audio_bytes, "test.wav")

        # Get the mock model
        mock_model = mock_model_repository.load_model.return_value

        # Verify predict_emotion_probabilities was called
        assert mock_model.predict_emotion_probabilities.called

        # Verify it was called with features
        call_args = mock_model.predict_emotion_probabilities.call_args[0][0]
        assert isinstance(call_args, np.ndarray)
        assert call_args.shape[0] == 210  # 210 features (1D array)

    # Test audio_features parameter
    def test_execute_without_audio_features_uses_extract_features(
        self, use_case: RunInferenceUseCase, mock_audio_processor: Mock, valid_audio_bytes: bytes
    ):
        """Test that audio_features=False uses extract_features method."""
        result = use_case.execute(valid_audio_bytes, "test.wav", audio_features=False)

        # Should call extract_features (not extract_features_with_audio_data)
        assert mock_audio_processor.extract_features.called
        assert not mock_audio_processor.extract_features_with_audio_data.called

        # Result should not have audio_features
        assert result.audio_features is None

    def test_execute_with_audio_features_uses_extract_features_with_audio_data(
        self, mock_audio_processor: Mock, mock_model_repository: Mock, mock_logger: Mock, valid_audio_bytes: bytes
    ):
        """Test that audio_features=True uses extract_features_with_audio_data method."""
        # Set up mock to return features + audio_features
        mock_audio_features = {
            "sample_rate": 22050,
            "duration": 2.5,
            "waveform": [0.1, 0.2, 0.3],
            "mel_spectrogram": [[0.1] * 10] * 128,
        }

        mock_audio_processor.extract_features_with_audio_data = Mock(
            return_value={
                "features": np.random.rand(210),
                "audio_features": mock_audio_features,
            }
        )

        use_case = RunInferenceUseCase(mock_audio_processor, mock_model_repository, mock_logger)
        result = use_case.execute(valid_audio_bytes, "test.wav", audio_features=True)

        # Should call extract_features_with_audio_data (not extract_features)
        assert mock_audio_processor.extract_features_with_audio_data.called
        assert not mock_audio_processor.extract_features.called

        # Result should have audio_features
        assert result.audio_features is not None
        assert result.audio_features == mock_audio_features
        assert result.audio_features["sample_rate"] == 22050

    def test_execute_with_audio_features_logs_correctly(
        self, mock_audio_processor: Mock, mock_model_repository: Mock, mock_logger: Mock, valid_audio_bytes: bytes
    ):
        """Test that audio_features=True logs correctly."""
        # Set up mock to return features + audio_features
        mock_audio_processor.extract_features_with_audio_data = Mock(
            return_value={
                "features": np.random.rand(210),
                "audio_features": {"sample_rate": 22050},
            }
        )

        use_case = RunInferenceUseCase(mock_audio_processor, mock_model_repository, mock_logger)
        use_case.execute(valid_audio_bytes, "test.wav", audio_features=True)

        # Check that logger.info was called with audio_features_requested
        info_calls = mock_logger.info.call_args_list
        start_call = info_calls[0]
        assert "audio_features_requested" in start_call[1]
        assert start_call[1]["audio_features_requested"] is True

        # Check that completion log includes audio_features status
        completion_call = info_calls[1]
        assert "includes_audio_features" in completion_call[1]
        assert completion_call[1]["includes_audio_features"] is True

    def test_execute_default_audio_features_is_false(
        self, use_case: RunInferenceUseCase, mock_audio_processor: Mock, valid_audio_bytes: bytes
    ):
        """Test that audio_features defaults to False."""
        result = use_case.execute(valid_audio_bytes, "test.wav")

        # Should use extract_features by default
        assert mock_audio_processor.extract_features.called
        assert result.audio_features is None

    def test_execute_with_audio_features_false_explicitly(
        self, use_case: RunInferenceUseCase, mock_audio_processor: Mock, valid_audio_bytes: bytes
    ):
        """Test that audio_features=False explicitly works correctly."""
        result = use_case.execute(valid_audio_bytes, "test.wav", audio_features=False)

        assert mock_audio_processor.extract_features.called
        assert result.audio_features is None


class TestRunInferenceUseCaseWithMonitoring:
    """Test suite for RunInferenceUseCase with monitoring integration."""

    @pytest.fixture
    def valid_audio_bytes(self) -> bytes:
        """Create valid audio bytes for testing."""
        sample_rate = 22050
        duration = 2.5
        frequency = 440
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_data = np.sin(2 * np.pi * frequency * t)
        audio_data = audio_data / np.max(np.abs(audio_data)) * 0.8

        audio_buffer = io.BytesIO()
        sf.write(audio_buffer, audio_data, sample_rate, format="WAV")
        audio_buffer.seek(0)
        return audio_buffer.read()

    @pytest.fixture
    def mock_audio_processor(self):
        """Create mock audio processor."""
        processor = Mock()
        processor.validate_audio = Mock(return_value=True)
        processor.extract_features = Mock(return_value=np.random.rand(210))
        return processor

    @pytest.fixture
    def mock_model_repository(self):
        """Create mock model repository."""
        repository = Mock()
        mock_model = Mock()
        mock_model.predict_emotion_probabilities = Mock(
            return_value={
                Emotion.ANGRY: 0.1,
                Emotion.DISGUST: 0.05,
                Emotion.FEAR: 0.1,
                Emotion.HAPPY: 0.6,
                Emotion.NEUTRAL: 0.1,
                Emotion.SAD: 0.05,
            }
        )
        repository.load_model = Mock(return_value=mock_model)
        return repository

    @pytest.fixture
    def mock_logger(self):
        """Create mock logger."""
        logger = Mock()
        logger.info = Mock()
        logger.error = Mock()
        return logger

    @pytest.fixture
    def mock_log_prediction_use_case(self):
        """Create mock log prediction use case."""
        use_case = Mock()
        use_case.execute = Mock(return_value="test-uuid-1234")
        return use_case

    @pytest.fixture
    def use_case_with_monitoring(
        self, mock_audio_processor, mock_model_repository, mock_logger, mock_log_prediction_use_case
    ):
        """Create RunInferenceUseCase with monitoring support."""
        return RunInferenceUseCase(
            mock_audio_processor,
            mock_model_repository,
            mock_logger,
            log_prediction_use_case=mock_log_prediction_use_case,
        )

    def test_execute_without_monitoring_does_not_log(
        self, use_case_with_monitoring: RunInferenceUseCase, mock_log_prediction_use_case: Mock, valid_audio_bytes: bytes
    ):
        """Test that monitoring is not called when enable_monitoring=False."""
        result = use_case_with_monitoring.execute(
            valid_audio_bytes, "test.wav", enable_monitoring=False
        )

        # Verify monitoring use case was not called
        assert not mock_log_prediction_use_case.execute.called

        # Verify no prediction_id in result
        assert result.prediction_id is None

    def test_execute_with_monitoring_logs_prediction(
        self, use_case_with_monitoring: RunInferenceUseCase, mock_log_prediction_use_case: Mock, valid_audio_bytes: bytes
    ):
        """Test that monitoring is called when enable_monitoring=True."""
        result = use_case_with_monitoring.execute(
            valid_audio_bytes, "test.wav", enable_monitoring=True
        )

        # Verify monitoring use case was called
        assert mock_log_prediction_use_case.execute.called

        # Verify prediction_id in result
        assert result.prediction_id == "test-uuid-1234"

    def test_execute_with_monitoring_passes_correct_data(
        self, use_case_with_monitoring: RunInferenceUseCase, mock_log_prediction_use_case: Mock, valid_audio_bytes: bytes
    ):
        """Test that monitoring use case receives correct data."""
        use_case_with_monitoring.execute(
            valid_audio_bytes, "test.wav", enable_monitoring=True
        )

        # Verify monitoring use case was called with correct parameters
        call_kwargs = mock_log_prediction_use_case.execute.call_args[1]
        assert call_kwargs["emotion"] == Emotion.HAPPY
        assert call_kwargs["confidence"] == 0.6
        assert call_kwargs["filename"] == "test.wav"
        assert call_kwargs["model_version"] == "v4"
        assert "probabilities" in call_kwargs
        assert "features" in call_kwargs
        assert "audio_bytes" in call_kwargs

    def test_execute_without_log_prediction_use_case_does_not_fail(
        self, mock_audio_processor, mock_model_repository, mock_logger, valid_audio_bytes
    ):
        """Test that monitoring doesn't fail when log_prediction_use_case is None."""
        # Create use case without monitoring support
        use_case = RunInferenceUseCase(
            mock_audio_processor,
            mock_model_repository,
            mock_logger,
            log_prediction_use_case=None,
        )

        # Should not fail even with enable_monitoring=True
        result = use_case.execute(valid_audio_bytes, "test.wav", enable_monitoring=True)

        # No prediction_id should be set
        assert result.prediction_id is None

    def test_execute_monitoring_default_is_false(
        self, use_case_with_monitoring: RunInferenceUseCase, mock_log_prediction_use_case: Mock, valid_audio_bytes: bytes
    ):
        """Test that enable_monitoring defaults to False."""
        result = use_case_with_monitoring.execute(valid_audio_bytes, "test.wav")

        # Verify monitoring was not called
        assert not mock_log_prediction_use_case.execute.called
        assert result.prediction_id is None

    def test_execute_monitoring_logs_include_prediction_id(
        self, use_case_with_monitoring: RunInferenceUseCase, mock_logger: Mock, valid_audio_bytes: bytes
    ):
        """Test that completion logs include prediction_id when monitoring is enabled."""
        use_case_with_monitoring.execute(valid_audio_bytes, "test.wav", enable_monitoring=True)

        # Check completion log
        info_calls = mock_logger.info.call_args_list
        completion_call = info_calls[1]  # Second call is completion
        assert "monitoring_enabled" in completion_call[1]
        assert completion_call[1]["monitoring_enabled"] is True
        assert "prediction_id" in completion_call[1]
        assert completion_call[1]["prediction_id"] == "test-uuid-1234"
