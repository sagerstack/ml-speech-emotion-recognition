"""Shared sidebar component for all pages."""
import os
from pathlib import Path

import streamlit as st

from real_inference import get_backend_health

# Configuration
ENABLE_MOCK_MODE = os.getenv("ENABLE_MOCK_MODE", "false").lower() == "true"

# Page paths
BASE_DIR = Path(__file__).resolve().parent
MODEL_PERFORMANCE_PAGE = BASE_DIR / "pages" / "4_Model Performance.py"


@st.cache_data(ttl=30, show_spinner=False)
def get_backend_health_cached():
    """Cache backend health check with 30-second TTL to auto-refresh status"""
    return get_backend_health()


def get_backend_status():
    """Get backend health status and determine which backend to use"""
    backend_healthy = get_backend_health_cached()
    force_mock = st.session_state.get("force_mock_mode", ENABLE_MOCK_MODE)
    use_real_backend = backend_healthy and not force_mock

    return use_real_backend, backend_healthy, force_mock


def render_sidebar():
    """Render the shared sidebar component."""
    with st.sidebar:
        # Custom CSS for left-aligned link buttons, page links, and consistent spacing
        st.markdown("""
        <style>
        /* Reduce spacing between all sidebar elements */
        .stSidebar [data-testid="stVerticalBlockBorderWrapper"] > div {
            margin-bottom: 0 !important;
            padding-bottom: 0 !important;
        }
        .stSidebar hr {
            margin: 0.75rem 0 !important;
        }
        .stSidebar a[kind="secondary"] {
            justify-content: flex-start !important;
            text-align: left !important;
        }
        .stSidebar [data-testid="stPageLink"] {
            width: fit-content !important;
        }
        .stSidebar [data-testid="stPageLink"] a {
            border: 1px solid currentColor !important;
            border-radius: 0.5rem !important;
            padding: 0.4rem 0.75rem !important;
            opacity: 0.8;
            font-size: 0.85rem !important;
        }
        .stSidebar [data-testid="stPageLink"] a:hover {
            opacity: 1;
        }
        .stSidebar [data-testid="stLinkButton"] {
            margin-top: 0.25rem !important;
        }
        .stSidebar [data-testid="stLinkButton"] a {
            font-size: 0.85rem !important;
        }
        </style>
        """, unsafe_allow_html=True)

        # Home section
        st.markdown("<p style='font-size: 0.85rem; margin: 0 0 0.75rem 0;'>🏠 <span style='text-decoration: underline;'>Home</span></p>", unsafe_allow_html=True)
        home_page = st.session_state.get("_page_home")
        if home_page:
            st.page_link(home_page, label="Emotion Inference")

        st.divider()

        # Model Performance section
        st.markdown("<p style='font-size: 0.85rem; margin: 0 0 0.75rem 0;'>🧭 <span style='text-decoration: underline;'>Model Performance</span></p>", unsafe_allow_html=True)
        st.page_link(str(MODEL_PERFORMANCE_PAGE), label="📈 Drift Monitoring")

        st.divider()

        # Grafana dashboard links
        st.markdown("<p style='font-size: 0.85rem; margin: 0 0 0.75rem 0;'>📡 <span style='text-decoration: underline;'>Observability</span></p>", unsafe_allow_html=True)
        grafana_base = os.getenv("GRAFANA_URL", "/ml-ser/grafana")
        st.link_button(
            "📊 App Metrics",
            f"{grafana_base}/d/893b67e4-6d93-49db-9047-9df11b9c86dc/ser-app-dashboard",
        )
        st.link_button(
            "☸️ EKS Cluster",
            f"{grafana_base}/d/fe5807eb-0772-41d0-8d28-03838a5b9671/kubernetes-dashboard",
        )

        st.divider()
        st.markdown("<p style='font-size: 0.85rem; margin: 0 0 0.75rem 0;'>⚙️ <span style='text-decoration: underline;'>Connection Status</span></p>", unsafe_allow_html=True)

        # Backend selection controls
        use_real_backend, backend_healthy, _ = get_backend_status()

        # Get the current force mock mode state
        force_mock_enabled = st.session_state.get("force_mock_mode", ENABLE_MOCK_MODE)

        # Determine status icons
        if force_mock_enabled:
            api_icon = "🟣"
            sagemaker_icon = "🟣"
        elif use_real_backend and backend_healthy:
            api_icon = "✅"
            sagemaker_icon = "✅"
        elif not backend_healthy:
            api_icon = "❌"
            sagemaker_icon = "❌"
        else:
            api_icon = "🟡"
            sagemaker_icon = "🟡"

        # Display status bullets
        st.markdown(f"<p style='margin: 0.25rem 0;'>{api_icon} Emotion API</p>", unsafe_allow_html=True)
        st.markdown(f"<p style='margin: 0.25rem 0;'>{sagemaker_icon} SageMaker</p>", unsafe_allow_html=True)

        # Refresh button - above mock mode toggle (only visible if mock mode is not enabled)
        if not force_mock_enabled:
            st.markdown("<style>div[data-testid='stButton'] button p { font-size: 0.85rem; }</style>", unsafe_allow_html=True)
            if st.button("🔗 Refresh", key="test_api_health_btn"):
                get_backend_health_cached.clear()
                with st.spinner("Testing API connection..."):
                    get_backend_health()
                    st.rerun()

        # Backend mode toggle (smaller font)
        st.markdown("""
        <style>
        .stSidebar [data-testid="stWidgetLabel"] p {
            font-size: 0.85rem;
        }
        </style>
        """, unsafe_allow_html=True)
        st.toggle(
            "Enable Mock Mode",
            value=ENABLE_MOCK_MODE,
            key="force_mock_mode",
            help="Enable to always use mock inference regardless of backend availability"
        )
