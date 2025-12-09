import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from requests.exceptions import RequestException

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api_client import get_api_client
from sidebar import render_sidebar


def _format_pct(value: float | None, decimals: int = 1) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.{decimals}f}%"


def _format_float(value: float | None, decimals: int = 3) -> str:
    if value is None:
        return "—"
    return f"{value:.{decimals}f}"


def render_model_performance() -> None:
    st.title("🧭 Model Performance")
    st.caption("Live view of Evidently metrics, drift signals, and model metadata.")

    # Render shared sidebar
    render_sidebar()

    client = get_api_client()

    try:
        history = client.fetch_monitoring_metrics_history()
    except RequestException as exc:
        st.error(f"Unable to fetch monitoring metrics history: {exc}")
        return

    try:
        summary = client.fetch_monitoring_summary()
    except RequestException as exc:
        summary = {}
        st.warning(f"Monitoring summary unavailable: {exc}")

    try:
        model_info = client.get_latest_model_info()
    except RequestException as exc:
        model_info = {}
        st.warning(f"Model metadata unavailable: {exc}")

    snapshots = history.get("snapshots") or []
    latest = history.get("latest") or {}
    df = pd.DataFrame(snapshots)

    if df.empty:
        st.info("No monitoring snapshots yet. Generate a few inferences to populate the dashboard.")
        return

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")

    buffer_stats = (summary or {}).get("buffer", {})
    total_predictions = buffer_stats.get("total_records", 0)
    latest_accuracy = latest.get("accuracy")
    accurate_predictions = (
        int(round(total_predictions * latest_accuracy)) if latest_accuracy is not None else None
    )

    st.subheader("Model metadata")
    meta_cols = st.columns(4)
    meta_cols[0].metric("Version", model_info.get("version", "—"))
    meta_cols[1].metric("Model Type", model_info.get("model_type", "—"))
    meta_cols[2].metric("Feature Dim", model_info.get("feature_dimension", "—"))
    meta_cols[3].metric("Available", "Yes" if model_info.get("available", False) else "No")

    st.subheader("Prediction throughput")
    stats_cols = st.columns(3)
    stats_cols[0].metric("Predictions Made", total_predictions)
    stats_cols[1].metric(
        "Accurate Predictions",
        accurate_predictions if accurate_predictions is not None else "—",
        _format_pct(latest_accuracy) if latest_accuracy is not None else None,
    )
    stats_cols[2].metric("Snapshots Collected", history.get("count", len(df)))

    st.divider()
    st.subheader("Classification quality (latest)")
    metric_cols = st.columns(4)
    metric_cols[0].metric("Accuracy", _format_pct(latest_accuracy))
    metric_cols[1].metric("Precision", _format_pct(latest.get("precision")))
    metric_cols[2].metric("Recall", _format_pct(latest.get("recall")))
    metric_cols[3].metric("F1 Score", _format_pct(latest.get("f1")))

    st.subheader("Performance Over Time")
    perf_df = df.melt(
        id_vars="timestamp",
        value_vars=["accuracy", "precision", "recall", "f1"],
        var_name="metric",
        value_name="value",
    )
    perf_fig = px.line(
        perf_df,
        x="timestamp",
        y="value",
        color="metric",
        labels={"value": "Score", "timestamp": "Timestamp"},
        markers=True,
    )
    perf_fig.update_layout(margin=dict(t=40, r=10, l=10, b=10), legend_title_text="")
    st.plotly_chart(perf_fig, use_container_width=True)

    st.divider()
    st.subheader("Drift signals (latest)")
    drift_cols = st.columns(4)
    drift_cols[0].metric(
        "Drifted Features (%)",
        _format_pct(latest.get("drifted_features_share")),
    )
    drift_cols[1].metric(
        "Drifted Features (#)",
        latest.get("drifted_features_count", "—"),
    )
    drift_cols[2].metric(
        "Prediction Drift (p-value)",
        _format_float(latest.get("prediction_drift")),
    )
    drift_cols[3].metric(
        "Label Drift (p-value)",
        _format_float(latest.get("label_drift")),
    )

    st.subheader("Drift Trends Over Time")
    drift_trend_df = df.melt(
        id_vars="timestamp",
        value_vars=["drifted_features_share", "prediction_drift", "label_drift"],
        var_name="metric",
        value_name="value",
    )
    drift_fig = px.line(
        drift_trend_df,
        x="timestamp",
        y="value",
        color="metric",
        labels={"value": "Value", "timestamp": "Timestamp"},
        markers=True,
    )
    drift_fig.update_layout(margin=dict(t=40, r=10, l=10, b=10), legend_title_text="")
    st.plotly_chart(drift_fig, use_container_width=True)

    st.subheader("Concept Drift Detection")
    concept_df = df[["timestamp", "accuracy", "f1"]].rename(
        columns={"accuracy": "Accuracy", "f1": "F1 Score"}
    )
    concept_fig = px.line(
        concept_df,
        x="timestamp",
        y=["Accuracy", "F1 Score"],
        labels={"value": "Score", "timestamp": "Timestamp", "variable": "Metric"},
        markers=True,
    )
    concept_fig.update_layout(margin=dict(t=40, r=10, l=10, b=10), legend_title_text="")
    st.plotly_chart(concept_fig, use_container_width=True)

    st.divider()
    st.subheader("Raw metrics payload")
    st.json(history)


render_model_performance()
