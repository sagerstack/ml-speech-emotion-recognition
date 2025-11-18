"""
Pytest configuration and fixtures for Streamlit frontend tests
"""

import pytest
import responses
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock
import numpy as np
import librosa
import soundfile as sf
from io import BytesIO


class MockSessionState(dict):
    """Mock session state that behaves like a dict but supports attribute access"""

    def __getattr__(self, name):
        if name in self:
            return self[name]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        if name in self:
            del self[name]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __contains__(self, key):
        return dict.__contains__(self, key)

    def get(self, key, default=None):
        return dict.get(self, key, default)

    def setdefault(self, key, default=None):
        return dict.setdefault(self, key, default)

# Add the streamlit_app directory to Python path
streamlit_app_path = Path(__file__).parent.parent / "streamlit_app"
sys.path.insert(0, str(streamlit_app_path))


@pytest.fixture
def mock_responses():
    """Mock responses for API testing"""
    return {
        "health_success": {
            "status": "healthy",
            "timestamp": "2024-01-01T00:00:00Z",
            "version": "1.0.0"
        },
        "health_error": {
            "status": "error",
            "message": "Service unavailable"
        },
        "prediction_success": {
            "emotion": "happy",
            "confidence": 0.85,
            "probabilities": {
                "happy": 0.85,
                "neutral": 0.10,
                "sad": 0.03,
                "angry": 0.01,
                "fearful": 0.005,
                "disgusted": 0.005
            },
            "processing_time": 1.23,
            "model_info": {
                "name": "emotion-recognition-v1",
                "version": "1.0.0"
            }
        },
        "prediction_error": {
            "detail": "Invalid audio format"
        },
        "supported_formats": {
            "supported_formats": ["wav", "mp3", "flac", "m4a"],
            "max_file_size": 25000000,
            "max_duration": 30
        },
        "model_info": {
            "model_name": "emotion-recognition-v1",
            "version": "1.0.0",
            "supported_emotions": ["happy", "sad", "angry", "fearful", "disgusted", "neutral"],
            "accuracy": 0.92
        }
    }


@pytest.fixture
def sample_audio_file():
    """Create a sample WAV audio file for testing"""
    # Generate a simple sine wave audio
    sample_rate = 22050
    duration = 2.0  # 2 seconds
    frequency = 440  # A4 note

    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio_data = np.sin(2 * np.pi * frequency * t) * 0.3  # 30% volume

    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    sf.write(temp_file.name, audio_data, sample_rate)

    yield temp_file.name

    # Cleanup
    os.unlink(temp_file.name)


@pytest.fixture
def sample_large_audio_file():
    """Create a large audio file that exceeds size limits"""
    sample_rate = 22050
    duration = 120.0  # 2 minutes (too large)
    frequency = 440

    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio_data = np.sin(2 * np.pi * frequency * t) * 0.3

    temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    sf.write(temp_file.name, audio_data, sample_rate)

    yield temp_file.name

    os.unlink(temp_file.name)


@pytest.fixture
def sample_invalid_audio_file():
    """Create an invalid audio file (corrupted)"""
    temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    # Write invalid data that looks like audio but isn't
    temp_file.write(b"This is not a valid WAV file")
    temp_file.close()

    yield temp_file.name

    os.unlink(temp_file.name)


@pytest.fixture
def mock_uploaded_file(sample_audio_file):
    """Mock Streamlit uploaded file object"""
    mock_file = Mock()
    mock_file.name = os.path.basename(sample_audio_file)
    mock_file.type = "audio/wav"
    mock_file.getvalue = lambda: open(sample_audio_file, 'rb').read()

    with open(sample_audio_file, 'rb') as f:
        mock_file.read = f.read
        mock_file.seek = f.seek

    return mock_file


@pytest.fixture
def mock_streamlit_session_state():
    """Mock Streamlit session state"""
    return {
        'api_client': None,
        'audio_processor': None,
        'prediction_history': [],
        'dashboard': None,
        'api_url': 'http://localhost:8000',
        'sagemaker_endpoint': 'test-emotion-endpoint',
        'use_local_model': True,
        'auto_refresh': False,
        'refresh_interval': 30,
        'debug_mode': False,
        'max_file_size': 10
    }


@pytest.fixture
def mock_streamlit():
    """Mock Streamlit module"""
    st_mock = Mock()

    # Mock session_state with custom mock that supports both dict and attribute access
    st_mock.session_state = MockSessionState()
    st_mock.sidebar = Mock()
    st_mock.cache_data = Mock()
    st_mock.cache_data.clear = Mock()

    # Mock UI elements
    st_mock.title = Mock()
    st_mock.header = Mock()
    st_mock.subheader = Mock()
    st_mock.text_input = Mock(return_value="http://localhost:8000")
    st_mock.button = Mock(return_value=False)
    st_mock.slider = Mock(return_value=30)
    st_mock.checkbox = Mock(return_value=False)
    st_mock.selectbox = Mock(return_value="🎵 Audio Analysis")
    st_mock.file_uploader = Mock(return_value=None)
    st_mock.audio = Mock()
    st_mock.spinner = Mock()
    st_mock.success = Mock()
    st_mock.error = Mock()
    st_mock.info = Mock()
    st_mock.warning = Mock()
    st_mock.metric = Mock()
    st_mock.columns = Mock(return_value=[Mock(), Mock()])
    st_mock.markdown = Mock()
    st_mock.pyplot = Mock()
    st_mock.dataframe = Mock()
    st_mock.json = Mock()
    st_mock.rerun = Mock()
    st_mock.tabs = Mock(return_value=[Mock(), Mock(), Mock()])

    return st_mock


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Setup test environment for all tests"""
    # Mock Streamlit
    mock_streamlit_module = Mock()

    # Mock session_state with custom mock that supports both dict and attribute access
    mock_streamlit_module.session_state = MockSessionState()

    # Mock page config
    mock_streamlit_module.set_page_config = Mock()

    # Mock custom CSS
    mock_streamlit_module.markdown = Mock()

    # Mock other common functions
    mock_streamlit_module.title = Mock()
    mock_streamlit_module.header = Mock()
    mock_streamlit_module.subheader = Mock()
    mock_streamlit_module.sidebar = Mock()
    mock_streamlit_module.text_input = Mock(return_value="http://localhost:8000")
    mock_streamlit_module.button = Mock(return_value=False)
    mock_streamlit_module.slider = Mock(return_value=30)
    mock_streamlit_module.checkbox = Mock(return_value=False)
    mock_streamlit_module.selectbox = Mock(return_value="🎵 Audio Analysis")
    mock_streamlit_module.file_uploader = Mock(return_value=None)
    mock_streamlit_module.audio = Mock()

    # Mock spinner with context manager support
    mock_spinner = Mock()
    mock_spinner.__enter__ = Mock(return_value=mock_spinner)
    mock_spinner.__exit__ = Mock(return_value=None)
    mock_streamlit_module.spinner = Mock(return_value=mock_spinner)

    mock_streamlit_module.success = Mock()
    mock_streamlit_module.error = Mock()
    mock_streamlit_module.info = Mock()
    mock_streamlit_module.warning = Mock()
    mock_streamlit_module.metric = Mock()

    # Mock columns with context manager support
    mock_col1 = Mock()
    mock_col1.__enter__ = Mock(return_value=mock_col1)
    mock_col1.__exit__ = Mock(return_value=None)
    mock_col2 = Mock()
    mock_col2.__enter__ = Mock(return_value=mock_col2)
    mock_col2.__exit__ = Mock(return_value=None)
    mock_streamlit_module.columns = Mock(return_value=[mock_col1, mock_col2])

    mock_streamlit_module.pyplot = Mock()
    mock_streamlit_module.dataframe = Mock()
    mock_streamlit_module.json = Mock()
    mock_streamlit_module.rerun = Mock()

    # Mock tabs with context manager support
    mock_tab1 = Mock()
    mock_tab1.__enter__ = Mock(return_value=mock_tab1)
    mock_tab1.__exit__ = Mock(return_value=None)
    mock_tab2 = Mock()
    mock_tab2.__enter__ = Mock(return_value=mock_tab2)
    mock_tab2.__exit__ = Mock(return_value=None)
    mock_tab3 = Mock()
    mock_tab3.__enter__ = Mock(return_value=mock_tab3)
    mock_tab3.__exit__ = Mock(return_value=None)
    mock_streamlit_module.tabs = Mock(return_value=[mock_tab1, mock_tab2, mock_tab3])
    mock_streamlit_module.cache_data = Mock()
    mock_streamlit_module.cache_data.clear = Mock()

    # Patch streamlit in all modules - use sys.modules to patch globally
    sys.modules['streamlit'] = mock_streamlit_module

    # Mock other dependencies that might cause issues in testing
    mock_pil = Mock()
    mock_pil.Image = Mock()
    sys.modules['PIL.Image'] = mock_pil.Image

    mock_matplotlib = Mock()
    mock_matplotlib.pyplot = Mock()
    mock_matplotlib.pyplot.subplots = Mock(return_value=(Mock(), Mock()))
    sys.modules['matplotlib.pyplot'] = mock_matplotlib.pyplot

    mock_seaborn = Mock()
    sys.modules['seaborn'] = mock_seaborn


@pytest.fixture
def api_test_urls():
    """Various API URLs for testing"""
    return {
        "valid": "http://localhost:8000",
        "invalid": "http://localhost:9999",
        "malformed": "not-a-url",
        "timeout": "http://10.255.255.1:8000",  # Unreachable IP
        "wrong_path": "http://localhost:8000/wrong-path"
    }


@pytest.fixture
def http_status_test_cases():
    """Test cases for different HTTP status codes"""
    return [
        (200, "success", "✅ API connection successful!"),
        (404, "not_found", "❌ API connection failed"),
        (500, "server_error", "❌ API returned unhealthy status"),
        (503, "service_unavailable", "❌ API returned unhealthy status"),
        (0, "connection_error", "❌ Connection failed: "),
        (timeout, "timeout", "❌ Connection error: "),
    ]