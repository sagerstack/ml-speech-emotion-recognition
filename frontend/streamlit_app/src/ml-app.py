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
import requests

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
MONITORING_PAGE = BASE_DIR / "pages" / "3_Monitoring.py"

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

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_model_metadata():
    """Fetch latest model metadata from backend API"""
    try:
        response = requests.get(
            f"{ML_APP_BASE_URL}/v1/models/local/latest",
            timeout=15  # Increased timeout for EKS deployment
        )
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"Failed to fetch model metadata: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error fetching model metadata: {str(e)}")
        return None

def display_model_metadata_card():
    """Display a card showing current model metadata"""
    use_real_backend, backend_healthy, force_mock = get_backend_status()

    # If mock mode is explicitly enabled, show mock indicator
    if force_mock:
        st.markdown("""
        <div style="background: #f3f4f6; border: 2px solid #9333ea; padding: 14px 18px;
                    border-radius: 8px; color: #374151; font-size: 13px;">
            <div style="font-weight: 600; margin-bottom: 6px; color: #6b7280;">
                🎭 Current Mode
            </div>
            <div style="font-size: 12px; color: #6b7280;">
                • <strong>Mode:</strong> Mock (Simulated Results)
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    # If backend is unavailable and mock is not forced, show Model Offline
    if not backend_healthy:
        st.markdown("""
        <div style="background: #f3f4f6; border: 2px solid #ef4444; padding: 14px 18px;
                    border-radius: 8px; color: #374151; font-size: 13px;">
            <div style="font-weight: 600; margin-bottom: 6px; color: #dc2626;">
                ⚠️ Model Offline
            </div>
            <div style="font-size: 12px; color: #6b7280;">
                • Backend is unavailable. Please check backend connection.
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Try to fetch metadata from backend
    metadata = fetch_model_metadata()

    if metadata:
        model_name = metadata.get('model_name', 'N/A')
        version = metadata.get('version', 'N/A')
        model_type = metadata.get('model_type', 'N/A')
        features = metadata.get('feature_dimension', 'N/A')
        classes = metadata.get('num_classes', 'N/A')
        dataset = metadata.get('dataset', 'N/A')
        description = metadata.get('description', '')

        st.markdown(f"""
        <div style="background: #f3f4f6; border: 2px solid #10b981; padding: 14px 18px;
                    border-radius: 8px; color: #374151; font-size: 13px;">
            <div style="font-weight: 600; margin-bottom: 10px; color: #1f2937;">
                🤖 Model Online
            </div>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px 16px;
                        font-size: 12px; color: #4b5563;">
                <div>• <strong>Model Version:</strong> v{version}</div>
                <div>• <strong>Model Name:</strong> {model_name}</div>
                <div>• <strong>Model Type:</strong> {model_type}</div>
                <div>• <strong>Feature Dimension:</strong> {features}</div>
                <div>• <strong>Number of Classes:</strong> {classes}</div>
                <div>• <strong>Training Dataset:</strong> {dataset}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Backend is healthy but can't fetch metadata - show warning
        st.markdown("""
        <div style="background: #f3f4f6; border: 2px solid #ef4444; padding: 14px 18px;
                    border-radius: 8px; color: #374151; font-size: 13px;">
            <div style="font-weight: 600; margin-bottom: 6px; color: #dc2626;">
                ⚠️ Model Offline
            </div>
            <div style="font-size: 12px; color: #6b7280;">
                • Unable to fetch model metadata from backend
            </div>
        </div>
        """, unsafe_allow_html=True)

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
VARIANT_KEY = "codex_iter5_variant"


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
    # Use chroma_cqt instead of chroma_stft to avoid streamlit caching issues
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)

    # Feature summary
    rms = float(librosa.feature.rms(y=y).mean())
    centroid = float(librosa.feature.spectral_centroid(y=y, sr=sr).mean())
    zcr = float(librosa.feature.zero_crossing_rate(y).mean())
    # Removed librosa.yin pitch calculation to avoid streamlit caching issues
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    mfcc_std = float(np.std(mfcc))

    feature_rows = [
        ("RMS Energy", f"{rms:.3f}", "Linear"),
        ("Spectral Centroid", f"{centroid:.1f} Hz", "Frequency"),
        ("Zero Crossing Rate", f"{zcr:.3f}", "Rate"),
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

        # Display model metadata at the top
        display_model_metadata_card()
        st.markdown("<br>", unsafe_allow_html=True)

        # Input audio selection toggle
        audio_input_mode = st.radio(
            "Select Input Audio Mode",
            options=["Audio File", "Live Recording"],
            horizontal=True,
            key="audio_input_mode",
        )
        st.markdown("<br>", unsafe_allow_html=True)

        # Initialize upload and recording variables
        upload = None
        recording = None

        # Show only the selected input control
        if audio_input_mode == "Audio File":
            upload = st.file_uploader(
                "Upload Audio File",
                type=["wav", "mp3", "flac", "m4a"],
                key="iter6-upload",
            )
        else:  # Live Recording
            recording = st.audio_input("Record Live Audio", key="iter6-record")

        # Single playback control for the selected audio
        if upload:
            st.audio(upload)
        elif recording:
            st.audio(recording)

        # Always use local inference endpoint
        engine = "local"

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

                # Update history after successful inference
                use_real_backend, _, _ = get_backend_status()
                backend_type = "API backend" if use_real_backend else "Mock mode"
                st.session_state[STATUS_KEY] = f"✅ {filename} processed via {backend_type}."
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


def _top_probabilities(probabilities: dict[str, float], top_n: int = 5):
    """Return sorted list of (emotion, prob) tuples."""
    return sorted(probabilities.items(), key=lambda item: item[1], reverse=True)[:top_n]


def _probability_hbar(probabilities: dict[str, float], accent: str = "#be185d", height: int = 230, top_n: int = 5):
    """Compact horizontal bar chart for top probabilities."""
    top_items = _top_probabilities(probabilities, top_n=top_n)
    if not top_items:
        return go.Figure()
    emotions = [emo.title() for emo, _ in top_items][::-1]
    values = [prob for _, prob in top_items][::-1]
    fig = go.Figure(
        go.Bar(
            x=values,
            y=emotions,
            orientation="h",
            marker=dict(color=accent, opacity=0.9),
            text=[f"{v:.1%}" for v in values],
            textposition="auto",
            hovertemplate="%{y}: %{x:.1%}<extra></extra>",
        )
    )
    fig.update_layout(
        height=height,
        margin=dict(l=70, r=20, t=30, b=30),
        template="plotly_white",
        xaxis=dict(tickformat=".0%", range=[0, 1]),
        yaxis=dict(tickfont=dict(size=11)),
    )
    return fig


def _emotion_color(emotion: str) -> str:
    """Map emotion to accent color."""
    colors = {
        "happy": "#f59e0b",
        "surprised": "#22c55e",
        "angry": "#ef4444",
        "fearful": "#6366f1",
        "fear": "#6366f1",
        "sad": "#3b82f6",
        "neutral": "#6b7280",
        "disgust": "#a855f7",
        "calm": "#10b981",
    }
    return colors.get(emotion.lower(), "#be185d")


def _latency_bar(latency_breakdown: dict[str, float], processing_time_ms: float):
    """Stacked horizontal bar for latency phases."""
    phases = latency_breakdown or {
        "ingest": processing_time_ms * 0.1 / 1000,
        "feature": processing_time_ms * 0.4 / 1000,
        "inference": processing_time_ms * 0.4 / 1000,
        "post": processing_time_ms * 0.1 / 1000,
    }
    colors = ["#0ea5e9", "#22c55e", "#f59e0b", "#a855f7"]
    fig = go.Figure()
    for idx, (name, seconds) in enumerate(phases.items()):
        fig.add_trace(
            go.Bar(
                x=[seconds * 1000],
                y=["Latency"],
                orientation="h",
                name=name.title(),
                marker_color=colors[idx % len(colors)],
                hovertemplate=f"{name.title()}: {{x:.1f}} ms<extra></extra>",
            )
        )
    fig.update_layout(
        barmode="stack",
        height=110,
        margin=dict(l=70, r=20, t=10, b=20),
        template="plotly_white",
        xaxis=dict(title="ms", tickformat=".0f"),
        showlegend=False,
    )
    return fig


def _hero_block(emotion: str, icon_name: str, confidence: float, accent: str = "#be185d"):
    """Render primary emotion hero block."""
    st.markdown(
        f"""
        <div style="padding: 0.5rem 0 0.25rem 0;">
            <div style="display: flex; align-items: center; gap: 0.75rem;">
                <span class="material-symbols-rounded" style="font-size: 72px; color: {accent}; line-height: 1;">{icon_name}</span>
                <div>
                    <div style="font-size: 30px; font-weight: 700; color: var(--text-color, inherit);">{emotion.title()}</div>
                    <div style="font-size: 14px; color: var(--text-color, inherit); opacity: 0.85;">Primary emotion</div>
                </div>
            </div>
            <div style="margin-top: 0.75rem; display: inline-flex; align-items: center; gap: 0.35rem; background: {accent}12; color: {accent}; padding: 0.35rem 0.7rem; border-radius: 999px; font-weight: 600; font-size: 13px;">
                <span class="material-symbols-rounded" style="font-size: 18px;">verified</span>
                {confidence:.0%} confidence
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _metadata_grid(metadata: dict):
    """Two-column label/value grid for model metadata."""
    left, right = st.columns(2)
    with left:
        st.markdown(f"**Model Name:** {metadata.get('model_name', 'N/A')}")
        st.markdown(f"**Architecture:** {metadata.get('model_type', 'N/A')}")
        st.markdown(f"**Feature Extraction:** {metadata.get('feature_extraction', 'N/A')}")
    with right:
        st.markdown(f"**Feature Dimension:** {metadata.get('feature_dimension', 'N/A')}")
        st.markdown(f"**Training Dataset:** {metadata.get('dataset', 'N/A')}")
        st.markdown(f"**Created Date:** {metadata.get('created_date', 'N/A')}")
    st.markdown(f"**Emotion Classes:** {', '.join(metadata.get('classes', []))}")


def _probability_table(probabilities: dict[str, float], highlight_top: bool = True):
    """Compact dataframe for probabilities."""
    rows = []
    sorted_probs = _top_probabilities(probabilities, top_n=len(probabilities))
    top_value = sorted_probs[0][1] if sorted_probs else None
    for emo, prob in sorted_probs:
        rows.append(
            {
                "Emotion": emo.title(),
                "Probability": prob,
                "Percent": f"{prob:.1%}",
                "🏆": "🏆" if highlight_top and prob == top_value else "",
            }
        )
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True, column_config={"Probability": st.column_config.NumberColumn(format="%.3f")})


def render_variant_compact_cards(payload: dict):
    """Variant 1: Compact two-column with hero and stacked cards."""
    left, right = st.columns([1, 1.2])
    with left:
        _hero_block(payload["emotion"], payload["icon_name"], payload["confidence"])
        st.plotly_chart(_probability_hbar(payload["probabilities"], accent="#f97316"), use_container_width=True)
        st.markdown("**Latency**")
        st.plotly_chart(_latency_bar(payload["latency_breakdown"], payload["processing_time_ms"]), use_container_width=True)

    with right:
        metric_col1, metric_col2, metric_col3 = st.columns(3)
        metric_col1.metric("Confidence", f"{payload['confidence']:.0%}")
        metric_col2.metric("Processing Time", f"{payload['processing_time_ms']:.1f} ms")
        metric_col3.metric("Model Version", f"v{payload['model_version']}")

        with st.container(border=True):
            st.info("Model Information")
            _metadata_grid(payload["metadata"])


# Single available layout
VARIANT_RENDERERS = {
    "Compact Cards": render_variant_compact_cards,
}


def stage_inference_results(result: AnalysisResult | None):
    """
    Display inference results using the Compact Cards layout.
    """
    with st.container(border=True):
        st.markdown("#### Stage 3 · Inference Results")
        if result is None:
            st.info("Run inference to see results here.")
            return

        # Check backend status
        use_real_backend, _, force_mock = get_backend_status()

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

        model_version = metadata.get("version", "2")
        icon_name = get_emotion_icon(emotion)
        perf_color, perf_label = get_performance_color(processing_time_ms)

        audio_blob = st.session_state.get(AUDIO_DATA_KEY, {})
        # Input data preview
        with st.container(border=True):
            st.markdown("**Input Data**")
            st.markdown(f"**{audio_blob.get('filename', getattr(result, 'source', 'Audio Input'))}**")
            if audio_blob.get("bytes"):
                st.audio(audio_blob["bytes"])
            else:
                st.caption("Audio preview unavailable.")

        payload = {
            "emotion": emotion,
            "confidence": confidence,
            "processing_time_ms": processing_time_ms,
            "model_version": model_version,
            "icon_name": icon_name,
            "perf_color": perf_color,
            "perf_label": perf_label,
            "metadata": metadata,
            "probabilities": result.probabilities,
            "latency_breakdown": getattr(result, "latency_breakdown", {}),
            "use_real_backend": use_real_backend,
            "audio_label": audio_blob.get("filename", getattr(result, "source", "Audio Input")),
            "audio_bytes": audio_blob.get("bytes"),
            "result": result,
        }

        render_variant_compact_cards(payload)


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
            st.Page(
                str(MONITORING_PAGE),
                title="Monitoring",
                icon="🔍",
            ),
        ],
        position="top",
        expanded=False,
    )
    current_page.run()
