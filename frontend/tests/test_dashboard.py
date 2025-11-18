"""
Tests for the Streamlit dashboard component
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from pathlib import Path

# Add the app directory to path
streamlit_app_path = Path(__file__).parent.parent / "streamlit_app"
sys.path.insert(0, str(streamlit_app_path))

# Import after conftest has set up proper mocking
import streamlit as st
from components.dashboard import Dashboard


class TestDashboard:
    """Test cases for Dashboard component"""

    @pytest.fixture
    def mock_api_client(self):
        """Mock API client for dashboard"""
        return Mock()

    @pytest.fixture
    def dashboard(self, mock_api_client):
        """Create Dashboard instance for testing"""
        return Dashboard(mock_api_client)

    @pytest.fixture
    def mock_streamlit_components(self):
        """Mock Streamlit components"""
        mocks = {
            'header': Mock(),
            'subheader': Mock(),
            'metric': Mock(),
            'columns': Mock(return_value=[Mock(), Mock(), Mock()]),
            'dataframe': Mock(),
            'pyplot': Mock(),
            'markdown': Mock(),
            'info': Mock(),
            'success': Mock(),
            'error': Mock(),
            'warning': Mock(),
            'spinner': Mock(),
            'button': Mock(return_value=False),
            'selectbox': Mock(return_value="Overview"),
            'tabs': Mock(return_value=[Mock(), Mock(), Mock()]),
            'cache_data': Mock(),
            'cache_data.clear': Mock()
        }

        # Set up mock streamlit module
        for func_name, mock_func in mocks.items():
            setattr(st, func_name, mock_func)

        return mocks

    def test_dashboard_init(self, mock_api_client):
        """Test Dashboard initialization"""
        dashboard = Dashboard(mock_api_client)
        assert dashboard.api_client == mock_api_client

    @patch('components.dashboard.st')
    def test_dashboard_render_overview(self, mock_st, dashboard, mock_streamlit_components):
        """Test rendering dashboard overview"""
        # Setup mocks
        mock_st.columns.return_value = [Mock(), Mock(), Mock()]
        mock_st.metric = Mock()

        # Mock API responses
        health_response = {"status": "healthy", "uptime": 3600}
        model_info = {"model_name": "emotion-v1", "accuracy": 0.92}
        recent_predictions = [{"emotion": "happy", "confidence": 0.85}]

        dashboard.api_client.health_check.return_value = health_response
        dashboard.api_client.get_model_info.return_value = model_info
        dashboard.api_client.get_recent_predictions.return_value = recent_predictions

        # Mock the render_overview method
        with patch.object(dashboard, 'render_overview') as mock_render:
            dashboard.render_full_dashboard()
            mock_render.assert_called_once()

    @patch('components.dashboard.st')
    def test_dashboard_health_check_success(self, mock_st, dashboard):
        """Test successful health check display"""
        health_response = {
            "status": "healthy",
            "uptime": 3600,
            "version": "1.0.0",
            "checks": {
                "database": "pass",
                "sagemaker": "pass",
                "storage": "pass"
            }
        }

        dashboard.api_client.health_check.return_value = health_response

        # Mock display components
        mock_st.metric = Mock()
        mock_st.success = Mock()

        # Test health check display
        dashboard._display_health_status()

        # Verify success message
        mock_st.success.assert_called_once()

    @patch('components.dashboard.st')
    def test_dashboard_health_check_failure(self, mock_st, dashboard):
        """Test failed health check display"""
        health_response = {"status": "error", "message": "Service unavailable"}

        dashboard.api_client.health_check.return_value = health_response

        # Mock display components
        mock_st.error = Mock()

        # Test health check display
        dashboard._display_health_status()

        # Verify error message
        mock_st.error.assert_called_once()

    @patch('components.dashboard.st')
    def test_dashboard_model_info_display(self, mock_st, dashboard):
        """Test model information display"""
        model_info = {
            "model_name": "emotion-recognition-v1",
            "version": "1.0.0",
            "accuracy": 0.92,
            "supported_emotions": ["happy", "sad", "angry", "fearful", "disgusted", "neutral"],
            "training_data": "CREMA-D"
        }

        dashboard.api_client.get_model_info.return_value = model_info

        # Mock display components
        mock_st.info = Mock()
        mock_st.metric = Mock()

        # Test model info display
        dashboard._display_model_info()

        # Verify model info is displayed
        mock_st.info.assert_called()
        mock_st.metric.assert_called()

    @patch('components.dashboard.st')
    def test_dashboard_recent_predictions_display(self, mock_st, dashboard):
        """Test recent predictions display"""
        recent_predictions = [
            {"emotion": "happy", "confidence": 0.85, "timestamp": "2024-01-01T10:00:00Z"},
            {"emotion": "sad", "confidence": 0.78, "timestamp": "2024-01-01T09:55:00Z"},
            {"emotion": "neutral", "confidence": 0.91, "timestamp": "2024-01-01T09:50:00Z"}
        ]

        dashboard.api_client.get_recent_predictions.return_value = recent_predictions

        # Mock display components
        mock_st.dataframe = Mock()
        mock_st.subheader = Mock()

        # Test recent predictions display
        dashboard._display_recent_predictions()

        # Verify predictions are displayed
        mock_st.dataframe.assert_called_once()
        mock_st.subheader.assert_called_once()

    @patch('components.dashboard.st')
    def test_dashboard_api_error_handling(self, mock_st, dashboard):
        """Test dashboard handling of API errors"""
        # Mock API client raising exception
        dashboard.api_client.health_check.side_effect = Exception("API unavailable")

        # Mock display components
        mock_st.error = Mock()

        # Test error handling
        dashboard._display_health_status()

        # Verify error is displayed
        mock_st.error.assert_called_once()
        error_message = mock_st.error.call_args[0][0]
        assert "API unavailable" in error_message

    @patch('components.dashboard.st')
    def test_dashboard_refresh_functionality(self, mock_st, dashboard):
        """Test dashboard data refresh functionality"""
        # Setup mocks
        mock_st.button.return_value = True  # Refresh button clicked
        mock_st.spinner = Mock()
        mock_st.cache_data = Mock()
        mock_st.cache_data.clear = Mock()

        # Test refresh
        dashboard.refresh_data()

        # Verify cache is cleared
        mock_st.cache_data.clear.assert_called_once()

    @patch('components.dashboard.st')
    def test_dashboard_empty_data_handling(self, mock_st, dashboard):
        """Test dashboard handling of empty data"""
        # Mock empty API responses
        dashboard.api_client.health_check.return_value = None
        dashboard.api_client.get_model_info.return_value = None
        dashboard.api_client.get_recent_predictions.return_value = []

        # Mock display components
        mock_st.info = Mock()
        mock_st.warning = Mock()

        # Test empty data handling
        dashboard.render_overview()

        # Verify appropriate messages are shown
        mock_st.warning.assert_called()

    @patch('components.dashboard.st')
    def test_dashboard_loading_state(self, mock_st, dashboard):
        """Test dashboard loading state display"""
        # Mock loading spinner
        mock_st.spinner.return_value.__enter__ = Mock()
        mock_st.spinner.return_value.__exit__ = Mock()

        # Mock API responses
        dashboard.api_client.health_check.return_value = {"status": "healthy"}

        # Test loading state
        dashboard._display_health_status()

        # Verify spinner is used
        mock_st.spinner.assert_called_once()

    @patch('components.dashboard.st')
    def test_dashboard_tab_navigation(self, mock_st, dashboard):
        """Test dashboard tab navigation"""
        # Mock tab selection
        mock_st.tabs.return_value = [Mock(), Mock(), Mock()]
        mock_st.selectbox.return_value = "Analytics"

        # Test tab navigation
        selected_tab = dashboard.get_selected_tab()

        # Verify tab selection works
        assert selected_tab == "Analytics"

    @patch('components.dashboard.st')
    def test_dashboard_export_functionality(self, mock_st, dashboard):
        """Test dashboard data export functionality"""
        # Mock export button
        mock_st.button.return_value = True
        mock_st.success = Mock()

        # Mock data
        export_data = [{"emotion": "happy", "confidence": 0.85}]

        # Test export
        dashboard.export_data(export_data, "predictions.csv")

        # Verify success message
        mock_st.success.assert_called_once()