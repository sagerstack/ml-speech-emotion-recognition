import pandas as pd
import plotly.express as px
import streamlit as st


def render_metrics():
    st.title("📊 Laboratory Metrics")
    st.caption("High-level telemetry derived from recent analysis runs.")

    history = st.session_state.get("codex_iter5_history", [])

    if not history:
        st.info("No history available. Run an analysis from Home to generate metrics.")
        return

    df = pd.DataFrame(history)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Analyses", len(df))
    col2.metric("Avg Confidence", f"{df['confidence'].mean():.0%}")
    col3.metric("Avg Latency", f"{df['processing_time'].mean():.2f}s")

    st.subheader("Emotion Distribution")
    emotion_fig = px.bar(
        df.groupby("emotion").size().reset_index(name="count"),
        x="emotion",
        y="count",
        color="emotion",
        color_discrete_sequence=px.colors.qualitative.Bold,
    )
    emotion_fig.update_layout(margin=dict(t=40, r=10, l=10, b=10))
    st.plotly_chart(emotion_fig, use_container_width=True)

    st.subheader("Engine Utilization")
    engine_fig = px.pie(
        df,
        names="engine",
        color="engine",
        color_discrete_sequence=px.colors.sequential.Bluered,
    )
    engine_fig.update_layout(margin=dict(t=40, r=10, l=10, b=10))
    st.plotly_chart(engine_fig, use_container_width=True)
