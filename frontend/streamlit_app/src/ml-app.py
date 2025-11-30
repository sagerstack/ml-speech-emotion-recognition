from datetime import datetime
from pathlib import Path
import io
import logging

import plotly.graph_objects as go
import streamlit as st
import streamlit_antd_components as stac
import pandas as pd
import numpy as np
import librosa

import os
from feature_charts import heatmap_chart, probability_bar, waveform_chart
from mock_inference import AnalysisResult
from real_inference import real_lab_backend, mock_lab_backend, get_backend_health
from api_client import ML_APP_BASE_URL

# Configure logging
logger = logging.getLogger(__name__)

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
    html, body, .stApp {
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
AUDIO_DATA_KEY = "codex_iter5_audio_data"
AUDIO_FEATURES_KEY = "codex_iter5_feature_summary"


def _load_audio_from_upload(file_obj) -> bytes:
    """Read bytes from an UploadedFile or BytesIO and reset pointer."""
    if hasattr(file_obj, "getbuffer"):
        data = file_obj.getbuffer().tobytes()
    else:
        data = file_obj.read()
    if hasattr(file_obj, "seek"):
        try:
            file_obj.seek(0)
        except Exception:
            pass
    return data


def _generate_local_features(audio_bytes: bytes, label: str, engine: str):
    """Compute local visualizations and feature stats for the uploaded audio."""
    y, sr = librosa.load(io.BytesIO(audio_bytes), sr=None)

    # Normalize waveform length for display
    max_wave_points = min(len(y), 4096)
    waveform = y[:max_wave_points]

    mel = librosa.power_to_db(
        librosa.feature.melspectrogram(y=y, sr=sr, n_mels=64, fmax=sr / 2),
        ref=np.max,
    )
    spectrogram = librosa.amplitude_to_db(np.abs(librosa.stft(y, n_fft=512)), ref=np.max)
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)

    # Feature summary
    rms = float(librosa.feature.rms(y=y).mean())
    centroid = float(librosa.feature.spectral_centroid(y=y, sr=sr).mean())
    zcr = float(librosa.feature.zero_crossing_rate(y).mean())
    pitch = float(librosa.yin(y, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C7')).mean())
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    mfcc_std = float(np.std(mfcc))

    feature_rows = [
        ("RMS Energy", f"{rms:.3f}", "Linear"),
        ("Spectral Centroid", f"{centroid:.1f} Hz", "Frequency"),
        ("Zero Crossing Rate", f"{zcr:.3f}", "Rate"),
        ("Pitch Mean", f"{pitch:.1f} Hz", "Frequency"),
        ("MFCC Spread", f"{mfcc_std:.3f}", "Std Dev"),
        ("Duration", f"{len(y)/sr:.1f} s", "Time"),
    ]

    feature_df = pd.DataFrame(feature_rows, columns=["Feature", "Value", "Units"])

    return {
        "label": label,
        "engine": engine,
        "sample_rate": sr,
        "waveform": waveform,
        "mel": mel,
        "spectrogram": spectrogram,
        "chroma": chroma,
        "feature_table": feature_df,
    }


def _store_audio_state(audio_bytes: bytes, label: str, engine: str, features: dict):
    """Persist audio bytes and computed features in session state."""
    st.session_state[AUDIO_DATA_KEY] = {
        "bytes": audio_bytes,
        "filename": label,
        "engine": engine,
        "timestamp": datetime.utcnow().isoformat(timespec="seconds"),
    }
    st.session_state[AUDIO_FEATURES_KEY] = features


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

            if upload:
                audio_source = upload
                label = upload.name or "uploaded-audio.wav"
            else:
                audio_source = recording
                label = f"live-recording-{datetime.utcnow().strftime('%H%M%S')}"

            try:
                audio_bytes = _load_audio_from_upload(audio_source)
                with st.spinner("Computing local audio features..."):
                    features = _generate_local_features(audio_bytes, label, engine)

                _store_audio_state(audio_bytes, label, engine, features)
                st.session_state[STATUS_KEY] = f"🔬 {label} analyzed locally. Ready for inference."
                st.session_state[PAGE_KEY] = None
                st.session_state[TAB_INDEX_KEY] = 1
                st.success(st.session_state[STATUS_KEY])
                st.rerun()
            except Exception as e:
                error_msg = f"Failed to process audio locally: {str(e)}"
                st.error(error_msg, icon="❌")
                if SHOW_DEBUG_INFO:
                    st.expander("Error Details").write(str(e))
                return None

    return st.session_state.get(AUDIO_FEATURES_KEY)


def stage_feature_analysis(feature_summary: dict | None):
    with st.container(border=True):
        st.markdown("#### Stage 2 · Feature Analysis")
        if feature_summary is None:
            st.info("Complete Stage 1 to visualize features.")
            return

        status_message = st.session_state.get(STATUS_KEY)
        if status_message:
            st.success(status_message)

        col1, col2 = st.columns([1.2, 1])
        with col1:
            st.plotly_chart(heatmap_chart(feature_summary["mel"], "Mel Spectrogram"), use_container_width=True)
            st.plotly_chart(waveform_chart(feature_summary["waveform"]), use_container_width=True)
        with col2:
            st.dataframe(feature_summary["feature_table"], use_container_width=True, hide_index=True)
            st.plotly_chart(heatmap_chart(feature_summary["spectrogram"], "Spectrogram"), use_container_width=True)

        st.markdown("##### 🎛️ Chroma Features")
        st.plotly_chart(heatmap_chart(feature_summary["chroma"], "Chroma"), use_container_width=True)

        if st.button("🚀 Predict Emotion", key="predict-emotion-btn", type="primary"):
            audio_blob = st.session_state.get(AUDIO_DATA_KEY)
            if not audio_blob:
                st.warning("Analyze audio first to enable prediction.", icon="⚠️")
                return
            backend = get_active_backend()
            audio_bytes = audio_blob["bytes"]
            engine = audio_blob["engine"]
            filename = audio_blob["filename"]
            try:
                file_obj = io.BytesIO(audio_bytes)
                file_obj.name = filename
                with st.spinner("Sending audio to inference backend..."):
                    result = backend.analyze(file_obj, engine=engine)

                st.session_state[PAGE_KEY] = result
                st.session_state[STATUS_KEY] = f"✅ {filename} processed via {engine}."

                # Update history after successful inference
                use_real_backend, _, _ = get_backend_status()
                history = st.session_state.setdefault("codex_iter5_history", [])
                history.insert(
                    0,
                    {
                        "timestamp": datetime.utcnow().isoformat(timespec="seconds"),
                        "source": filename,
                        "engine": engine,
                        "emotion": result.emotion,
                        "confidence": result.confidence,
                        "processing_time": result.processing_time,
                        "backend_type": "Real API" if use_real_backend else "Mock",
                    },
                )
                st.session_state["codex_iter5_history"] = history[:25]

                st.session_state[TAB_INDEX_KEY] = 2
                st.success(st.session_state[STATUS_KEY])
                st.rerun()
            except Exception as e:
                st.error(f"Failed to run inference: {str(e)}", icon="❌")
                if SHOW_DEBUG_INFO:
                    st.expander("Error Details").write(str(e))


def get_emotion_icon(emotion: str) -> str:
    """
    Get Material Symbols Rounded icon name for a given emotion.

    Args:
        emotion: Emotion name (e.g., 'happy', 'sad', 'angry')

    Returns:
        str: Material icon name
    """
    emotion_icons = {
        "angry": "sentiment_very_dissatisfied",
        "disgust": "sick",
        "fear": "sentiment_stressed",
        "fearful": "sentiment_stressed",
        "happy": "sentiment_very_satisfied",
        "neutral": "sentiment_neutral",
        "sad": "sentiment_dissatisfied",
        "surprised": "sentiment_excited",
        "calm": "sentiment_calm",
    }
    return emotion_icons.get(emotion.lower(), "sentiment_neutral")


def get_performance_color(time_ms: float) -> tuple[str, str]:
    """
    Get color and label for performance metrics based on processing time.

    Args:
        time_ms: Processing time in milliseconds

    Returns:
        tuple: (color_hex, performance_label)
    """
    if time_ms < 100:
        return "#10b981", "Fast"  # green
    elif time_ms < 500:
        return "#f59e0b", "Medium"  # yellow
    else:
        return "#ef4444", "Slow"  # red


def get_mock_inference_result() -> dict:
    """
    Generate mock inference result matching real API structure.

    Returns:
        dict: Mock inference response
    """
    return {
        "version": "2",
        "prediction": {
            "emotion": "happy",
            "confidence": 0.95,
            "all_probabilities": {
                "angry": 0.01,
                "disgust": 0.01,
                "fear": 0.01,
                "happy": 0.95,
                "neutral": 0.01,
                "sad": 0.01
            }
        },
        "model_info": {
            "type": "Pipeline (StandardScaler + RFE + SVC)",
            "features_used": 78
        },
        "processing_time_ms": 45.32
    }


def get_mock_model_metadata() -> dict:
    """
    Generate mock model metadata matching real API structure.

    Returns:
        dict: Mock metadata response
    """
    return {
        "version": "2",
        "model_name": "SVM with MFCC Features",
        "model_type": "Pipeline (StandardScaler + RFE + SVC)",
        "description": "Support Vector Machine with MFCC-based features and Recursive Feature Elimination",
        "feature_dimension": 78,
        "feature_extraction": "MFCCs with delta and delta-delta coefficients",
        "classes": ["angry", "disgust", "fear", "happy", "neutral", "sad"],
        "num_classes": 6,
        "created_date": "2024-01-20",
        "dataset": "CREMA-D",
        "notes": "Improved model with feature selection and SVM classifier"
    }


def fetch_latest_model_metadata() -> dict | None:
    """
    Fetch model metadata from the backend API.

    Returns:
        dict: Model metadata or None on error
    """
    try:
        import requests
        response = requests.get(
            f"{ML_APP_BASE_URL}/v1/models/local/latest",
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"Failed to fetch metadata: HTTP {response.status_code}")
            return None
    except Exception as e:
        logger.warning(f"Error fetching metadata: {str(e)}")
        return None


def stage_inference_results(result: AnalysisResult | None):
    """
    Display redesigned inference results with Material Icons and Ant Design cards.

    This function implements US-006 requirements:
    - Material Symbols Rounded icons for emotions
    - Ant Design cards for organized display
    - 2-column layout for balanced information density
    - Color-coded performance metrics
    - Real backend API integration with mock fallback

    Args:
        result: AnalysisResult from inference or None
    """
    with st.container(border=True):
        st.markdown("#### Stage 3 · Inference Results")
        if result is None:
            st.info("Inference results appear once Stage 1 is complete.")
            return

        # Check backend status
        use_real_backend, backend_healthy, force_mock = get_backend_status()

        # Fetch model metadata (try real API first, then fallback to mock)
        metadata = None
        if use_real_backend and not force_mock:
            metadata = fetch_latest_model_metadata()

        if metadata is None:
            metadata = get_mock_model_metadata()

        # Extract data from result
        emotion = result.emotion
        confidence = result.confidence
        processing_time_sec = result.processing_time
        processing_time_ms = processing_time_sec * 1000  # Convert to milliseconds

        # Get model version from metadata
        model_version = metadata.get("version", "2")

        # Get emotion icon
        icon_name = get_emotion_icon(emotion)

        # Get performance color and label
        perf_color, perf_label = get_performance_color(processing_time_ms)

        # === HERO SECTION: Primary Emotion with Large Icon ===
        st.markdown("### Primary Emotion")

        # Create centered layout for emotion display
        col_left, col_center, col_right = st.columns([1, 2, 1])
        with col_center:
            # Display large Material icon with emotion
            st.markdown(
                f"""
                <div style="text-align: center; padding: 1rem 0;">
                    <span class="material-symbols-rounded" style="font-size: 80px; color: #be185d;">
                        {icon_name}
                    </span>
                    <div style="font-size: 32px; font-weight: 600; margin-top: 0.5rem; color: #1f2937;">
                        {emotion.title()}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        # === METRICS ROW: Confidence, Processing Time, Model Version ===
        st.markdown("---")
        metric_col1, metric_col2, metric_col3 = st.columns(3)

        with metric_col1:
            st.metric("Confidence", f"{confidence:.0%}")

        with metric_col2:
            st.metric("Processing Time", f"{processing_time_ms:.2f} ms")

        with metric_col3:
            st.metric("Model Version", f"v{model_version}")

        st.markdown("---")

        # === TWO-COLUMN CARD LAYOUT ===
        col1, col2 = st.columns([1, 1])

        # LEFT COLUMN: Model Information Card
        with col1:
            st.markdown("##### 📊 Model Information")
            with st.container(border=True):
                # Extract fields from metadata
                model_name = metadata.get("model_name", "N/A")
                model_type = metadata.get("model_type", "N/A")
                feature_extraction = metadata.get("feature_extraction", "N/A")
                feature_dimension = metadata.get("feature_dimension", "N/A")
                dataset = metadata.get("dataset", "N/A")
                created_date = metadata.get("created_date", "N/A")
                emotion_classes = metadata.get("classes", [])

                # Display fields in label: value format
                st.markdown(f"**Model Name:** {model_name}")
                st.markdown(f"**Architecture:** {model_type}")
                st.markdown(f"**Feature Extraction:** {feature_extraction}")
                st.markdown(f"**Feature Dimension:** {feature_dimension}")
                st.markdown(f"**Training Dataset:** {dataset}")
                st.markdown(f"**Created Date:** {created_date}")
                st.markdown(f"**Emotion Classes:** {', '.join(emotion_classes)}")

        # RIGHT COLUMN: Model Description Card
        with col2:
            st.markdown("##### 📝 Model Description")
            with st.container(border=True):
                description = metadata.get("description", "No description available.")
                notes = metadata.get("notes", "")

                st.markdown(description)

                if notes:
                    st.markdown("---")
                    st.markdown("**Notes:**")
                    st.markdown(notes)

        # === SECOND ROW: Performance Metrics (Full Width) ===
        st.markdown("##### ⚡ Performance Metrics")
        with st.container(border=True):
            perf_col1, perf_col2 = st.columns([1, 3])

            with perf_col1:
                st.metric("Processing Time", f"{processing_time_ms:.2f} ms")
                st.markdown(f"**Performance:** {perf_label}")

            with perf_col2:
                # Create color-coded progress bar
                # Normalize to 0-100 scale (500ms = 100%)
                progress_value = min(processing_time_ms / 5, 100)  # Cap at 100%

                st.markdown(
                    f"""
                    <div style="margin-top: 1rem;">
                        <div style="background-color: #e5e7eb; border-radius: 8px; height: 24px; overflow: hidden;">
                            <div style="background-color: {perf_color}; width: {progress_value}%; height: 100%;
                                        display: flex; align-items: center; justify-content: center;
                                        color: white; font-weight: 600; font-size: 12px;">
                                {processing_time_ms:.2f} ms
                            </div>
                        </div>
                        <div style="margin-top: 0.5rem; font-size: 12px; color: #6b7280;">
                            <span style="color: #10b981;">● Fast (&lt;100ms)</span> &nbsp;
                            <span style="color: #f59e0b;">● Medium (100-500ms)</span> &nbsp;
                            <span style="color: #ef4444;">● Slow (≥500ms)</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        # === PROBABILITY DISTRIBUTION (Full Width) ===
        st.markdown("##### 🎭 Emotion Probability Distribution")
        st.plotly_chart(probability_bar(result.probabilities, accent="#facc15"), use_container_width=True)

        # === DETAILED SCORES TABLE ===
        st.markdown("##### 📈 Detailed Emotion Scores")
        emotion_data = []
        for emo, probability in result.probabilities.items():
            emotion_data.append({
                "Emotion": emo.title(),
                "Confidence": f"{probability:.3f}",
                "Percentage": f"{probability * 100:.1f}%",
                "Status": "🏆" if probability == confidence else ""
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
    inference_result = st.session_state.get(PAGE_KEY)
    feature_summary = st.session_state.get(AUDIO_FEATURES_KEY)

    if tab_choice == "Step 1 · Audio Capture":
        stage_audio_recording()
    elif tab_choice == "Step 2 · Feature Analysis":
        stage_feature_analysis(feature_summary)
    elif tab_choice == "Step 3 · Inference Results":
        stage_inference_results(inference_result)
    else:
        stage_audio_recording()


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
