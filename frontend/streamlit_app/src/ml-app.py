from datetime import datetime
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st
import streamlit_antd_components as stac

from feature_charts import heatmap_chart, probability_bar, waveform_chart
from mock_inference import AnalysisResult, lab_backend

st.set_page_config(
    page_title="Codex Iteration 5 · Speech Emotion Lab",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent
HISTORY_PAGE = BASE_DIR / "pages" / "1_History.py"
METRICS_PAGE = BASE_DIR / "pages" / "2_Metrics.py"

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
                type=["wav", "mp3", "flac"],
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
                "Route",
                ["local_studio", "sagemaker_prod", "dual_stack"],
                key="iter5-engine",
            )
            st.slider("Temperature", 0.0, 1.0, 0.35, 0.05, key="iter5-temp")
        action = st.button("Proceed", key="iter5-launch-btn")
        if action:
            if not upload and not recording:
                st.warning("You need to supply a file or record audio.", icon="⚠️")
                return None
            label = upload.name if upload else f"iter5-live-{datetime.utcnow().strftime('%H%M%S')}"
            result = lab_backend.analyze(label, engine=engine)
            st.session_state[PAGE_KEY] = result
            st.session_state[STATUS_KEY] = f"{label} queued on {engine}."
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
                },
            )
            st.session_state["codex_iter5_history"] = history[:25]
            st.session_state[TAB_INDEX_KEY] = 1
            st.success(st.session_state[STATUS_KEY])
            st.rerun()
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


def stage_inference_results(result: AnalysisResult | None):
    with st.container(border=True):
        st.markdown("#### Stage 3 · Inference Results")
        if result is None:
            st.info("Inference results appear once Stage 1 is complete.")
            return
        col1, col2, col3 = st.columns(3)
        col1.metric("Emotion", result.emotion.title())
        col2.metric("Confidence", f"{result.confidence:.0%}")
        col3.metric("Processing Time", f"{result.processing_time:.2f}s")
        st.plotly_chart(probability_bar(result.probabilities, accent="#facc15"), use_container_width=True)


def home_page():
    st.title("Speech Emotion Recognition")
    st.caption("A project to analyze and infer emotions from audio inputs.")

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
