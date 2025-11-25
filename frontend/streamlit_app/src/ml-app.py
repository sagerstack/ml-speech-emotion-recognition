from datetime import datetime
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st
import streamlit_antd_components as stac
import pandas as pd

import os
from feature_charts import heatmap_chart, probability_bar, waveform_chart
from mock_inference import AnalysisResult
from real_inference import real_lab_backend, mock_lab_backend, get_backend_health
from api_client import ML_APP_BASE_URL

st.set_page_config(
    page_title="Codex Iteration 5 · Speech Emotion Lab",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent
HISTORY_PAGE = BASE_DIR / "pages" / "1_History.py"
METRICS_PAGE = BASE_DIR / "pages" / "2_Metrics.py"

# Configuration
ENABLE_MOCK_MODE = os.getenv("ENABLE_MOCK_MODE", "false").lower() == "true"
FALLBACK_TO_MOCK = os.getenv("FALLBACK_TO_MOCK", "true").lower() == "true"
SHOW_DEBUG_INFO = os.getenv("SHOW_DEBUG_INFO", "true").lower() == "true"

# Initialize backend health status
@st.cache_resource
def get_backend_health_cached():
    """Cache backend health check to avoid repeated health checks"""
    return get_backend_health()

def get_backend_status():
    """Get backend health status and determine which backend to use"""
    backend_healthy = get_backend_health_cached()
    force_mock = st.session_state.get("force_mock_mode", ENABLE_MOCK_MODE)
    use_real_backend = backend_healthy and not force_mock

    return use_real_backend, backend_healthy, force_mock

def get_active_backend():
    """Get the active backend (real or mock)"""
    use_real_backend, _, _ = get_backend_status()
    return real_lab_backend if use_real_backend else mock_lab_backend

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inconsolata:wght@400;600&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded');
    html, body, [class*="st-"] {
        font-family: 'Inconsolata', monospace !important;
    }
    div.block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1rem !important;
    }
    div.stButton > button {
        background: #be185d !important;
        border: 1px solid #be185d !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        padding: 0.35rem 1.4rem !important;
        transition: all 0.2s ease !important;
    }
    div.stButton > button:hover {
        background: #9d174d !important;
        border-color: #9d174d !important;
    }
    div.stButton > button:focus-visible {
        outline: 2px solid rgba(190, 24, 93, 0.45) !important;
        outline-offset: 2px !important;
    }
    .material-icons, .material-symbols-rounded, [class*="material-icons"] {
        font-family: 'Material Symbols Rounded' !important;
        font-weight: normal !important;
        font-style: normal !important;
        font-size: 1.25rem;
        line-height: 1;
        letter-spacing: normal;
        text-transform: none;
        display: inline-block;
        white-space: nowrap;
    }
    [data-testid="collapsedControl"] button div p {
        display: none !important;
    }
    [data-testid="collapsedControl"] button::after {
        content: '⇤';
        font-size: 1.3rem;
        color: #be185d;
    }
    [data-testid="collapsedControl"] button[aria-expanded="false"]::after {
        content: '⇥';
    }
    </style>
    """,
    unsafe_allow_html=True,
)

TAB_ITEMS = [
    stac.TabsItem(label="Step 1 · Audio Capture"),
    stac.TabsItem(label="Step 2 · Feature Analysis"),
    stac.TabsItem(label="Step 3 · Inference Results"),
]
TAB_LABELS = [item.label for item in TAB_ITEMS]
PAGE_KEY = "codex_iter5_result"
TAB_INDEX_KEY = "codex_iter5_tab_index"
STATUS_KEY = "codex_iter5_status"


def stage_audio_recording() -> AnalysisResult | None:
    with st.container(border=True):
        st.markdown("### Stage 1 · Audio Recording")
        st.caption("Select an audio file or record live audio for analysis.")

        col1, col2, col3 = st.columns([1.4, 1, 1])
        with col1:
            upload = st.file_uploader(
                "Upload Audio File",
                type=["wav", "mp3", "flac", "m4a"],
                key="iter5-upload",
            )
            if upload:
                st.audio(upload)
        with col2:
            recording = st.audio_input("Record Live Audio", key="iter5-record")
            if recording:
                st.audio(recording)
        with col3:
            engine = st.selectbox(
                "Processing Engine",
                ["local", "sagemaker_prod", "dual_stack"],
                key="iter5-engine",
                help="local: Local processing\nsagemaker_prod: Production SageMaker endpoint\ndual_stack: Both for comparison"
            )
            st.slider("Confidence Threshold", 0.0, 1.0, 0.5, 0.05, key="iter5-confidence-threshold")

        action = st.button("🚀 Analyze Audio", key="iter5-launch-btn", type="primary")

        if action:
            if not upload and not recording:
                st.warning("You need to supply a file or record audio.", icon="⚠️")
                return None

            # Get the active backend
            backend = get_active_backend()

            # Prepare audio source
            if upload:
                audio_source = upload
                label = upload.name
            else:
                audio_source = recording
                label = f"live-recording-{datetime.utcnow().strftime('%H%M%S')}"

            try:
                # Show processing status
                with st.spinner(f"Analyzing audio with {backend.__class__.__name__}..."):
                    result = backend.analyze(audio_source, engine=engine)

                # Store result
                st.session_state[PAGE_KEY] = result
                st.session_state[STATUS_KEY] = f"✅ {label} analyzed successfully using {engine}."

                # Update history
                use_real_backend, _, _ = get_backend_status()
                history = st.session_state.setdefault("codex_iter5_history", [])
                history.insert(
                    0,
                    {
                        "timestamp": datetime.utcnow().isoformat(timespec="seconds"),
                        "source": label,
                        "engine": engine,
                        "emotion": result.emotion,
                        "confidence": result.confidence,
                        "processing_time": result.processing_time,
                        "backend_type": "Real API" if use_real_backend else "Mock",
                    },
                )
                st.session_state["codex_iter5_history"] = history[:25]
                st.session_state[TAB_INDEX_KEY] = 1

                st.success(st.session_state[STATUS_KEY])
                st.rerun()

            except Exception as e:
                error_msg = f"Failed to analyze audio: {str(e)}"
                st.error(error_msg, icon="❌")

                # Show detailed error in debug mode
                if SHOW_DEBUG_INFO:
                    st.expander("Error Details").write(str(e))

                return None

    return st.session_state.get(PAGE_KEY)


def stage_feature_analysis(result: AnalysisResult | None):
    with st.container(border=True):
        st.markdown("#### Stage 2 · Feature Analysis")
        if result is None:
            st.info("Complete Stage 1 to visualize features.")
            return
        status_message = st.session_state.get(STATUS_KEY)
        if status_message:
            st.success(status_message)
        col1, col2 = st.columns([1.2, 1])
        with col1:
            st.plotly_chart(heatmap_chart(result.visualizations["mel"], "Mel Spectrogram"), use_container_width=True)
            st.plotly_chart(waveform_chart(result.visualizations["waveform"]), use_container_width=True)
        with col2:
            st.dataframe(result.feature_tracks, use_container_width=True, hide_index=True)
            timeline_fig = go.Figure()
            timeline_fig.add_trace(
                go.Bar(
                    x=[entry["phase"] for entry in result.timeline],
                    y=[idx + 1 for idx, _ in enumerate(result.timeline)],
                    marker=dict(color="#38bdf8"),
                )
            )
            timeline_fig.update_layout(
                height=220,
                title="Processing Phases",
                yaxis=dict(showticklabels=False),
            )
            st.plotly_chart(timeline_fig, use_container_width=True)

        # Predict Emotion button
        if st.button("🚀 Predict Emotion", key="predict-emotion-btn", type="primary"):
            st.session_state[TAB_INDEX_KEY] = 2  # Switch to Step 3 tab (index 2)
            st.rerun()


def stage_inference_results(result: AnalysisResult | None):
    with st.container(border=True):
        st.markdown("#### Stage 3 · Inference Results")
        if result is None:
            st.info("Inference results appear once Stage 1 is complete.")
            return

        # Check if this is from real backend
        use_real_backend, _, _ = get_backend_status()

        # Main metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Primary Emotion", result.emotion.title())
        col2.metric("Confidence", f"{result.confidence:.0%}")
        col3.metric("Processing Time", f"{result.processing_time:.2f}s")

        # Probability distribution chart
        st.plotly_chart(probability_bar(result.probabilities, accent="#facc15"), use_container_width=True)

        # Additional metadata for real backend
        if use_real_backend and hasattr(result, 'audio_metadata') and result.audio_metadata:
            st.markdown("##### 📊 Audio Metadata")
            col1, col2, col3 = st.columns(3)
            col1.metric("Sample Rate", f"{result.audio_metadata.sample_rate} Hz")
            col2.metric("File Size", f"{result.audio_metadata.file_size_bytes:,} bytes")
            col3.metric("Duration", f"{result.audio_metadata.file_size_bytes / (result.audio_metadata.sample_rate * 2):.1f}s")

        # SageMaker metadata if available
        if use_real_backend and hasattr(result, 'inference_metadata') and result.inference_metadata:
            st.markdown("##### 🚀 SageMaker Inference Details")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Endpoint", result.inference_metadata.sagemaker_endpoint.split('-')[-1][:8] + "...")
            col2.metric("Region", result.inference_metadata.aws_region)
            col3.metric("Inference Time", f"{result.inference_metadata.invocation_time_seconds:.2f}s")
            col4.metric("Response Size", f"{result.inference_metadata.response_size_bytes} bytes")

        # Latency breakdown
        if hasattr(result, 'latency_breakdown') and result.latency_breakdown:
            st.markdown("##### ⏱️ Processing Latency Breakdown")
            latency_data = []
            for phase, time_taken in result.latency_breakdown.items():
                latency_data.append({
                    "Phase": phase.title(),
                    "Time (s)": f"{time_taken:.2f}",
                    "Percentage": f"{(time_taken / result.processing_time * 100):.1f}%"
                })
            latency_df = pd.DataFrame(latency_data)
            st.dataframe(latency_df, use_container_width=True, hide_index=True)

        # All emotion probabilities in detail
        st.markdown("##### 🎭 Detailed Emotion Scores")
        emotion_data = []
        for emotion, probability in result.probabilities.items():
            emotion_data.append({
                "Emotion": emotion.title(),
                "Confidence": f"{probability:.3f}",
                "Percentage": f"{probability * 100:.1f}%",
                "Status": "🏆" if probability == result.confidence else "  "
            })

        # Sort by confidence
        emotion_df = pd.DataFrame(emotion_data)
        emotion_df = emotion_df.sort_values("Confidence", ascending=False)
        st.dataframe(emotion_df, use_container_width=True, hide_index=True)


def home_page():
    st.title("Speech Emotion Recognition")
    st.caption("A project to analyze and infer emotions from audio inputs.")

    # Sidebar with backend information and controls
    with st.sidebar:
        st.markdown("## ⚙️ Backend Settings")

        # Backend selection controls
        use_real_backend, backend_healthy, _ = get_backend_status()

        # Backend mode toggle
        mock_mode = st.toggle(
            "Enable Mock Mode",
            value=ENABLE_MOCK_MODE,
            key="force_mock_mode",
            help="Enable to always use mock inference regardless of backend availability"
        )

        # Environment info
        st.markdown("### 📋 API Status")

        # Get the current force mock mode state
        force_mock_enabled = st.session_state.get("force_mock_mode", ENABLE_MOCK_MODE)

        if force_mock_enabled:
            st.info("🔵 Mock Mode (Forced)", icon="ℹ️")
        elif use_real_backend:
            st.success("✅ Active", icon="🟢")
        elif not backend_healthy:
            st.error("❌ Backend Unavailable", icon="🔴")
        else:
            st.warning("🟡 Using Mock (Fallback)", icon="⚠️")

        # API Configuration
        st.markdown("### 🌐 API Configuration")
        st.write(f"""
Base URL: {ML_APP_BASE_URL}
""")

        # Test API Health button (moved below API Configuration)
        if use_real_backend and not force_mock_enabled:
            if st.button("🔗 Test API Health", disabled=force_mock_enabled):
                with st.spinner("Testing API connection..."):
                    healthy = get_backend_health()
                    if healthy:
                        st.success("API is healthy!")
                    else:
                        st.error("API is not responding.")
        
    current_index = st.session_state.get(TAB_INDEX_KEY, 0)
    tab_choice = stac.tabs(
        items=TAB_ITEMS,
        index=current_index,
        variant="outline",
        color="#be185d",
        use_container_width=True,
        key="iter5-tabs",
    )
    try:
        selected_index = TAB_LABELS.index(tab_choice)
    except ValueError:
        selected_index = current_index
    st.session_state[TAB_INDEX_KEY] = selected_index
    result = st.session_state.get(PAGE_KEY)
    if tab_choice == "Step 1 · Audio Capture":
        result = stage_audio_recording()
    elif tab_choice == "Step 2 · Feature Analysis":
        stage_feature_analysis(result)
    elif tab_choice == "Step 3 · Inference Results":
        stage_inference_results(result)
    else:
        result = stage_audio_recording()
    if result is not None:
        st.session_state[PAGE_KEY] = result


if __name__ == "__main__":
    current_page = st.navigation(
        [
            st.Page(home_page, title="Home", icon="🏠"),
            st.Page(
                str(HISTORY_PAGE),
                title="History",
                icon="🕓",
            ),
            st.Page(
                str(METRICS_PAGE),
                title="Metrics",
                icon="📊",
            ),
        ],
        position="top",
        expanded=False,
    )
    current_page.run()
