"""
Tests for the main Streamlit application
Focus on UI components, navigation, and user interactions
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
import tempfile
import os
import sys
from pathlib import Path

# Add the app directory to path
streamlit_app_path = Path(__file__).parent.parent / "streamlit_app"
sys.path.insert(0, str(streamlit_app_path))

# Import app after conftest has set up proper mocking
from app import main, render_settings_page, display_emotion_results


class TestStreamlitApp:
    """Test cases for main Streamlit application"""

    @pytest.fixture
    def mock_streamlit_session_state(self):
        """Mock Streamlit session state"""
        return {
            'api_client': Mock(),
            'audio_processor': Mock(),
            'prediction_history': [],
            'dashboard': Mock(),
            'api_url': 'http://localhost:8000',
            'sagemaker_endpoint': 'test-emotion-endpoint',
            'use_local_model': True,
            'auto_refresh': False,
            'refresh_interval': 30,
            'debug_mode': False,
            'max_file_size': 10
        }

    @pytest.fixture
    def mock_streamlit_components(self):
        """Mock all Streamlit components"""
        mocks = {
            'set_page_config': Mock(),
            'markdown': Mock(),
            'sidebar': Mock(),
            'columns': Mock(return_value=[Mock(), Mock()]),
            'selectbox': Mock(return_value="🎵 Audio Analysis"),
            'button': Mock(return_value=False),
            'text_input': Mock(return_value="http://localhost:8000"),
            'slider': Mock(return_value=30),
            'checkbox': Mock(return_value=False),
            'file_uploader': Mock(return_value=None),
            'audio': Mock(),
            'spinner': Mock(),
            'success': Mock(),
            'error': Mock(),
            'info': Mock(),
            'warning': Mock(),
            'metric': Mock(),
            'header': Mock(),
            'subheader': Mock(),
            'dataframe': Mock(),
            'pyplot': Mock(),
            'json': Mock(),
            'rerun': Mock(),
            'tabs': Mock(return_value=[Mock(), Mock(), Mock()]),
            'cache_data': Mock(),
            'cache_data.clear': Mock()
        }

        # Set up mock streamlit module
        for func_name, mock_func in mocks.items():
            setattr(st, func_name, mock_func)

        # Mock session state
        st.session_state = Mock()
        st.session_state.__getitem__ = Mock(side_effect=lambda k: {
            'api_client': Mock(),
            'audio_processor': Mock(),
            'prediction_history': [],
            'dashboard': Mock(),
            'api_url': 'http://localhost:8000',
            'sagemaker_endpoint': 'test-emotion-endpoint',
            'use_local_model': True,
            'auto_refresh': False,
            'refresh_interval': 30,
            'debug_mode': False,
            'max_file_size': 10
        }.get(k))
        st.session_state.__contains__ = Mock(return_value=True)
        st.session_state.__setitem__ = Mock()

        return mocks

    @pytest.fixture
    def mock_dependencies(self):
        """Mock external dependencies"""
        mock_pil = Mock()
        mock_pil.Image = Mock()

        mock_matplotlib = Mock()
        mock_matplotlib.pyplot = Mock()
        mock_fig = Mock()
        mock_ax = Mock()
        mock_matplotlib.pyplot.subplots.return_value = (mock_fig, mock_ax)

        mock_seaborn = Mock()

        return {
            'PIL.Image': mock_pil.Image,
            'matplotlib.pyplot': mock_matplotlib.pyplot,
            'seaborn': mock_seaborn
        }

    @patch('app.st')
    @patch('app.APIClient')
    @patch('app.AudioProcessor')
    @patch('app.Dashboard')
    def test_main_page_configuration(self, mock_dashboard, mock_audio_processor,
                                  mock_api_client, mock_st):
        """Test main page configuration and setup"""
        # Setup mocks
        mock_api_client.return_value = Mock()
        mock_audio_processor.return_value = Mock()
        mock_dashboard.return_value = Mock()

        # Mock session state with custom behavior
        mock_st.session_state.__contains__ = Mock(return_value=False)
        mock_st.session_state.__setitem__ = Mock()
        mock_st.selectbox.return_value = "🎵 Audio Analysis"

        # Create column mocks that support context manager protocol
        mock_col1 = Mock()
        mock_col1.__enter__ = Mock(return_value=mock_col1)
        mock_col1.__exit__ = Mock(return_value=None)
        mock_col2 = Mock()
        mock_col2.__enter__ = Mock(return_value=mock_col2)
        mock_col2.__exit__ = Mock(return_value=None)
        mock_st.columns.return_value = [mock_col1, mock_col2]

        # Mock sidebar to support context manager
        mock_sidebar = Mock()
        mock_sidebar.__enter__ = Mock(return_value=mock_sidebar)
        mock_sidebar.__exit__ = Mock(return_value=None)
        mock_st.sidebar = mock_sidebar

        # Run main function
        main()

        # Note: set_page_config and session state initialization happen at import time
        # The important thing is that the main function runs without errors

        # Verify header is displayed
        mock_st.markdown.assert_any_call('<h1 class="main-header">🎭 Speech Emotion Recognition</h1>', unsafe_allow_html=True)

    @patch('app.st')
    @patch('app.APIClient')
    @patch('app.AudioProcessor')
    @patch('app.Dashboard')
    def test_main_navigation_dashboard(self, mock_dashboard, mock_audio_processor,
                                     mock_api_client, mock_st):
        """Test navigation to dashboard page"""
        # Setup mocks
        mock_dashboard_instance = Mock()
        mock_dashboard.return_value = mock_dashboard_instance

        # Setup session state mocking as both dict and object
        mock_session_state = Mock()
        mock_session_state.__contains__ = Mock(return_value=True)  # 'dashboard' in session_state
        mock_session_state.__getitem__ = Mock(return_value=mock_dashboard_instance)  # session_state['dashboard']
        mock_session_state.__setitem__ = Mock()  # session_state[key] = value
        mock_session_state.dashboard = mock_dashboard_instance  # session_state.dashboard
        mock_st.session_state = mock_session_state

        mock_st.selectbox.return_value = "📊 Dashboard"

        # Run main function
        main()

        # Verify dashboard is rendered
        mock_dashboard_instance.render_full_dashboard.assert_called_once()

    @patch('app.st')
    @patch('app.APIClient')
    @patch('app.AudioProcessor')
    @patch('app.Dashboard')
    def test_main_navigation_settings(self, mock_dashboard, mock_audio_processor,
                                    mock_api_client, mock_st, mock_dependencies):
        """Test navigation to settings page"""
        # Setup mocks
        mock_st.session_state.__contains__ = Mock(return_value=True)
        mock_st.selectbox.return_value = "⚙️ Settings"
        mock_st.tabs.return_value = [Mock(), Mock(), Mock()]

        # Mock render_settings_page
        with patch('app.render_settings_page') as mock_render_settings:
            main()
            mock_render_settings.assert_called_once()

    @patch('app.st')
    @patch('app.APIClient')
    @patch('app.AudioProcessor')
    @patch('app.Dashboard')
    def test_main_api_connection_test_success(self, mock_dashboard, mock_audio_processor,
                                            mock_api_client, mock_st):
        """Test successful API connection test"""
        # Setup mocks
        mock_api_client_instance = Mock()
        mock_api_client.return_value = mock_api_client_instance
        mock_st.session_state.__contains__ = Mock(return_value=True)
        mock_st.session_state.api_client = mock_api_client_instance
        mock_st.selectbox.return_value = "🎵 Audio Analysis"
        mock_st.text_input.return_value = "http://localhost:8000"
        mock_st.button.return_value = True  # Test button clicked
        mock_st.columns.return_value = [Mock(), Mock()]

        # Mock successful health check
        mock_api_client_instance.health_check.return_value = {"status": "healthy"}

        # Run main function
        main()

        # Verify API connection test was performed
        mock_api_client_instance.health_check.assert_called_once_with("http://localhost:8000")
        mock_st.success.assert_called_once_with("✅ API connection successful!")

    @patch('app.st')
    @patch('app.APIClient')
    @patch('app.AudioProcessor')
    @patch('app.Dashboard')
    def test_main_api_connection_test_failure(self, mock_dashboard, mock_audio_processor,
                                            mock_api_client, mock_st):
        """Test failed API connection test"""
        # Setup mocks
        mock_api_client_instance = Mock()
        mock_api_client.return_value = mock_api_client_instance
        mock_st.session_state.__contains__ = Mock(return_value=True)
        mock_st.session_state.api_client = mock_api_client_instance
        mock_st.selectbox.return_value = "🎵 Audio Analysis"
        mock_st.text_input.return_value = "http://localhost:8000"
        mock_st.button.return_value = True  # Test button clicked
        mock_st.columns.return_value = [Mock(), Mock()]

        # Mock failed health check
        mock_api_client_instance.health_check.return_value = {"status": "error"}

        # Run main function
        main()

        # Verify error message was displayed
        mock_st.error.assert_called_once_with("❌ API connection failed")

    @patch('app.st')
    @patch('app.APIClient')
    @patch('app.AudioProcessor')
    @patch('app.Dashboard')
    def test_main_api_connection_test_exception(self, mock_dashboard, mock_audio_processor,
                                             mock_api_client, mock_st):
        """Test API connection test with exception"""
        # Setup mocks
        mock_api_client_instance = Mock()
        mock_api_client.return_value = mock_api_client_instance
        mock_st.session_state.__contains__ = Mock(return_value=True)
        mock_st.session_state.api_client = mock_api_client_instance
        mock_st.selectbox.return_value = "🎵 Audio Analysis"
        mock_st.text_input.return_value = "http://localhost:8000"
        mock_st.button.return_value = True  # Test button clicked
        mock_st.columns.return_value = [Mock(), Mock()]

        # Mock exception during health check
        mock_api_client_instance.health_check.side_effect = Exception("Connection failed")

        # Run main function
        main()

        # Verify error message was displayed
        mock_st.error.assert_called_once()
        error_message = mock_st.error.call_args[0][0]
        assert "Connection error" in error_message

    @patch('app.st')
    @patch('app.APIClient')
    @patch('app.AudioProcessor')
    @patch('app.Dashboard')
    def test_main_file_upload_and_analysis(self, mock_dashboard, mock_audio_processor,
                                         mock_api_client, mock_st, sample_audio_file):
        """Test file upload and audio analysis workflow"""
        # Setup mocks
        mock_api_client_instance = Mock()
        mock_audio_processor_instance = Mock()
        mock_api_client.return_value = mock_api_client_instance
        mock_audio_processor.return_value = mock_audio_processor_instance
        mock_st.session_state.__contains__ = Mock(return_value=True)
        mock_st.session_state.api_client = mock_api_client_instance
        mock_st.session_state.audio_processor = mock_audio_processor_instance
        mock_st.session_state.prediction_history = []
        mock_st.selectbox.return_value = "🎵 Audio Analysis"
        mock_st.button.return_value = True  # Analyze button clicked
        mock_st.columns.return_value = [Mock(), Mock()]

        # Mock file upload
        mock_file = Mock()
        mock_file.name = "test_audio.wav"
        mock_file.type = "audio/wav"
        mock_st.file_uploader.return_value = mock_file

        # Mock audio processing
        audio_data = [0.1, 0.2, 0.3]  # Sample audio data
        sample_rate = 22050
        mock_audio_processor_instance.load_audio.return_value = (audio_data, sample_rate)

        # Mock prediction result
        prediction_result = {
            "emotion": "happy",
            "confidence": 0.85,
            "probabilities": {"happy": 0.85, "sad": 0.15},
            "processing_time": 1.23
        }
        mock_api_client_instance.predict_emotion.return_value = prediction_result

        # Run main function
        with patch('app.display_emotion_results') as mock_display_results:
            main()

            # Verify file upload was processed
            mock_st.file_uploader.assert_called_once()
            mock_st.audio.assert_called_once_with(mock_file, format="audio/wav")

            # Verify audio processing
            mock_audio_processor_instance.load_audio.assert_called_once_with(mock_file)

            # Verify prediction
            mock_api_client_instance.predict_emotion.assert_called_once()

            # Verify results display
            mock_display_results.assert_called_once_with(prediction_result)

            # Verify history was updated
            assert len(mock_st.session_state.prediction_history) == 1
            assert mock_st.session_state.prediction_history[0]["filename"] == "test_audio.wav"

    @patch('app.st')
    @patch('app.APIClient')
    @patch('app.AudioProcessor')
    @patch('app.Dashboard')
    def test_main_prediction_error_handling(self, mock_dashboard, mock_audio_processor,
                                          mock_api_client, mock_st):
        """Test error handling during prediction"""
        # Setup mocks
        mock_api_client_instance = Mock()
        mock_audio_processor_instance = Mock()
        mock_api_client.return_value = mock_api_client_instance
        mock_audio_processor.return_value = mock_audio_processor_instance
        mock_st.session_state.__contains__ = Mock(return_value=True)
        mock_st.session_state.api_client = mock_api_client_instance
        mock_st.session_state.audio_processor = mock_audio_processor_instance
        mock_st.session_state.prediction_history = []
        mock_st.selectbox.return_value = "🎵 Audio Analysis"
        mock_st.button.return_value = True  # Analyze button clicked
        mock_st.columns.return_value = [Mock(), Mock()]

        # Mock file upload
        mock_file = Mock()
        mock_st.file_uploader.return_value = mock_file

        # Mock audio processing success
        mock_audio_processor_instance.load_audio.return_value = ([0.1, 0.2, 0.3], 22050)

        # Mock prediction failure
        mock_api_client_instance.predict_emotion.return_value = None

        # Run main function
        main()

        # Verify error message was displayed
        mock_st.error.assert_called_with("❌ Failed to get emotion prediction")

        # Verify history was not updated
        assert len(mock_st.session_state.prediction_history) == 0

    @patch('app.st')
    @patch('app.APIClient')
    @patch('app.AudioProcessor')
    @patch('app.Dashboard')
    def test_main_audio_processing_error(self, mock_dashboard, mock_audio_processor,
                                       mock_api_client, mock_st):
        """Test error handling during audio processing"""
        # Setup mocks
        mock_api_client_instance = Mock()
        mock_audio_processor_instance = Mock()
        mock_api_client.return_value = mock_api_client_instance
        mock_audio_processor.return_value = mock_audio_processor_instance
        mock_st.session_state.__contains__ = Mock(return_value=True)
        mock_st.session_state.api_client = mock_api_client_instance
        mock_st.session_state.audio_processor = mock_audio_processor_instance
        mock_st.selectbox.return_value = "🎵 Audio Analysis"
        mock_st.button.return_value = True  # Analyze button clicked
        mock_st.columns.return_value = [Mock(), Mock()]

        # Mock file upload
        mock_file = Mock()
        mock_st.file_uploader.return_value = mock_file

        # Mock audio processing failure
        mock_audio_processor_instance.load_audio.side_effect = Exception("Invalid audio format")

        # Run main function
        main()

        # Verify error message was displayed
        mock_st.error.assert_called_once()
        error_message = mock_st.error.call_args[0][0]
        assert "Error processing audio" in error_message


class TestDisplayEmotionResults:
    """Test cases for emotion results display function"""

    @patch('app.st')
    @patch('app.plt')
    def test_display_emotion_results_high_confidence(self, mock_plt, mock_st):
        """Test displaying emotion results with high confidence"""
        # Setup matplotlib mock
        mock_fig = Mock()
        mock_ax = Mock()
        mock_plt.pyplot.subplots.return_value = (mock_fig, mock_ax)
        mock_bars = [Mock() for _ in range(6)]
        mock_ax.bar.return_value = mock_bars

        # Test data with high confidence
        result = {
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
            "processing_time": 1.23
        }

        # Call function
        display_emotion_results(result)

        # Verify header
        mock_st.header.assert_called_with("🎯 Emotion Prediction Results")

        # Verify metrics display
        assert mock_st.metric.call_count >= 3  # emotion, confidence, processing time

        # Verify confidence classification styling
        mock_st.markdown.assert_any_call(
            '<div class="emotion-result high-confidence">',
            unsafe_allow_html=True
        )

        # Verify chart creation
        mock_plt.pyplot.subplots.assert_called_once_with(figsize=(10, 6))

        # Verify dataframe display
        mock_st.dataframe.assert_called_once()

    @patch('app.st')
    @patch('app.plt')
    def test_display_emotion_results_medium_confidence(self, mock_plt, mock_st):
        """Test displaying emotion results with medium confidence"""
        mock_plt.pyplot.subplots.return_value = (Mock(), Mock())

        # Test data with medium confidence
        result = {
            "emotion": "neutral",
            "confidence": 0.65,
            "probabilities": {"neutral": 0.65, "happy": 0.35},
            "processing_time": 0.98
        }

        display_emotion_results(result)

        # Verify medium confidence styling
        mock_st.markdown.assert_any_call(
            '<div class="emotion-result medium-confidence">',
            unsafe_allow_html=True
        )

    @patch('app.st')
    @patch('app.plt')
    def test_display_emotion_results_low_confidence(self, mock_plt, mock_st):
        """Test displaying emotion results with low confidence"""
        mock_plt.pyplot.subplots.return_value = (Mock(), Mock())

        # Test data with low confidence
        result = {
            "emotion": "sad",
            "confidence": 0.45,
            "probabilities": {"sad": 0.45, "neutral": 0.30, "angry": 0.25},
            "processing_time": 2.1
        }

        display_emotion_results(result)

        # Verify low confidence styling
        mock_st.markdown.assert_any_call(
            '<div class="emotion-result low-confidence">',
            unsafe_allow_html=True
        )

    @patch('app.st')
    @patch('app.plt')
    def test_display_emotion_results_missing_data(self, mock_plt, mock_st):
        """Test displaying results with missing data"""
        mock_plt.pyplot.subplots.return_value = (Mock(), Mock())

        # Test data with missing fields
        result = {
            "emotion": "happy",
            "confidence": 0.0,  # Missing confidence
            # Missing probabilities
            "processing_time": 1.0
        }

        display_emotion_results(result)

        # Should still display basic metrics
        assert mock_st.metric.call_count >= 2

        # Should handle missing probabilities gracefully
        mock_st.dataframe.assert_called_once()


class TestRenderSettingsPage:
    """Test cases for settings page rendering"""

    @patch('app.st')
    def test_render_settings_page_api_settings_tab(self, mock_st):
        """Test API settings tab in settings page"""
        # Setup mocks
        mock_st.session_state.api_url = "http://localhost:8000"
        mock_st.session_state.sagemaker_endpoint = "test-endpoint"
        mock_st.session_state.use_local_model = True
        mock_st.tabs.return_value = [Mock(), Mock(), Mock()]
        mock_st.text_input.return_value = "http://localhost:8000"
        mock_st.button.return_value = False

        render_settings_page()

        # Verify tabs are created
        mock_st.tabs.assert_called_once()

        # Verify API URL input
        mock_st.text_input.assert_any_call(
            "Backend API URL",
            value="http://localhost:8000",
            help="URL of the FastAPI backend service"
        )

    @patch('app.st')
    @patch('app.APIClient')
    def test_render_settings_page_test_connection_success(self, mock_api_client, mock_st):
        """Test connection test in settings with success"""
        # Setup mocks
        mock_api_client_instance = Mock()
        mock_api_client.return_value = mock_api_client_instance
        mock_st.session_state.api_client = mock_api_client_instance
        mock_st.tabs.return_value = [Mock(), Mock(), Mock()]
        mock_st.columns.return_value = [Mock(), Mock()]
        mock_st.button.return_value = True  # Test connection button

        # Mock successful health check
        mock_api_client_instance.health_check.return_value = {"status": "healthy"}

        render_settings_page()

        # Verify success message
        mock_st.success.assert_called_once_with("✅ Connection successful!")
        mock_st.json.assert_called_once_with({"status": "healthy"})

    @patch('app.st')
    @patch('app.APIClient')
    def test_render_settings_page_test_connection_failure(self, mock_api_client, mock_st):
        """Test connection test in settings with failure"""
        # Setup mocks
        mock_api_client_instance = Mock()
        mock_api_client.return_value = mock_api_client_instance
        mock_st.session_state.api_client = mock_api_client_instance
        mock_st.tabs.return_value = [Mock(), Mock(), Mock()]
        mock_st.columns.return_value = [Mock(), Mock()]
        mock_st.button.return_value = True  # Test connection button

        # Mock failed health check
        mock_api_client_instance.health_check.return_value = {"status": "error"}

        render_settings_page()

        # Verify error message
        mock_st.error.assert_called_once_with("❌ API returned unhealthy status")

    @patch('app.st')
    def test_render_settings_page_appearance_settings(self, mock_st):
        """Test appearance settings in settings page"""
        # Setup mocks
        mock_st.session_state.auto_refresh = False
        mock_st.session_state.refresh_interval = 30
        mock_st.tabs.return_value = [Mock(), Mock(), Mock()]
        mock_st.selectbox.return_value = "Light"
        mock_st.checkbox.return_value = False
        mock_st.slider.return_value = 30

        render_settings_page()

        # Verify theme selection
        mock_st.selectbox.assert_called_once()

        # Verify auto-refresh checkbox
        mock_st.checkbox.assert_called_with(
            "Enable Auto-refresh",
            value=False,
            help="Automatically refresh dashboard data"
        )

    @patch('app.st')
    def test_render_settings_page_advanced_settings(self, mock_st):
        """Test advanced settings in settings page"""
        # Setup mocks
        mock_st.session_state.debug_mode = False
        mock_st.session_state.max_file_size = 10
        mock_st.tabs.return_value = [Mock(), Mock(), Mock()]
        mock_st.checkbox.return_value = False
        mock_st.slider.return_value = 10
        mock_st.button.return_value = False

        render_settings_page()

        # Verify debug mode checkbox
        mock_st.checkbox.assert_any_call(
            "Enable Debug Mode",
            value=False,
            help="Show additional debugging information"
        )

        # Verify max file size slider
        mock_st.slider.assert_any_call(
            "Max File Size (MB)",
            min_value=1,
            max_value=50,
            value=10,
            help="Maximum allowed audio file size"
        )