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

import os

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

    # Loading status for fetching model performance metrics
    with st.status("Loading model performance metrics...", expanded=True) as status:
        try:
            history = client.fetch_monitoring_metrics_history()
            status.update(label="Metrics loaded successfully!", state="complete", expanded=False)
        except RequestException as exc:
            status.update(label="Failed to load metrics", state="error")
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
    try:
        new_since_report = client.fetch_new_predictions_since_last_report()
    except RequestException as exc:
        new_since_report = {}
        st.warning(f"Unable to fetch predictions since last report: {exc}")

    # Create two-column layout for accordions (50-50 split)
    col1, col2 = st.columns([0.5, 0.5])

    with col1:
        # Model Information Accordion (includes throughput metrics)
        if model_info:
            # Prepare accordion title with model info and status
            model_name = model_info.get('model_name', 'Unknown Model')
            is_available = model_info.get('available', False)
            status_indicator = "🟢" if is_available else "❌"

            accordion_title = f"{model_name} {status_indicator}"

            with st.expander(accordion_title, expanded=True):
                info_col1, info_col2 = st.columns(2)

                with info_col1:
                    st.markdown('<p style="color: rgba(128, 128, 128, 0.8); margin-bottom: 10px;">Model Name:</p>', unsafe_allow_html=True)
                    st.markdown(f'<p style="color: inherit; margin-top: -15px; margin-bottom: 15px; font-size: 16px; font-weight: 500;">{model_info.get("model_name", "N/A")}</p>', unsafe_allow_html=True)
                    st.markdown('<p style="color: rgba(128, 128, 128, 0.8); margin-bottom: 10px;">Model Type:</p>', unsafe_allow_html=True)
                    st.markdown(f'<p style="color: inherit; margin-top: -15px; margin-bottom: 15px; font-size: 16px; font-weight: 500;">{model_info.get("model_type", "N/A")}</p>', unsafe_allow_html=True)

                with info_col2:
                    st.markdown('<p style="color: rgba(128, 128, 128, 0.8); margin-bottom: 10px;">Feature Dimension:</p>', unsafe_allow_html=True)
                    st.markdown(f'<p style="color: inherit; margin-top: -15px; margin-bottom: 15px; font-size: 16px; font-weight: 500;">{model_info.get("feature_dimension", "N/A")}</p>', unsafe_allow_html=True)
                    st.markdown('<p style="color: rgba(128, 128, 128, 0.8); margin-bottom: 10px;">Number of Classes:</p>', unsafe_allow_html=True)
                    st.markdown(f'<p style="color: inherit; margin-top: -15px; margin-bottom: 15px; font-size: 16px; font-weight: 500;">{model_info.get("num_classes", "N/A")}</p>', unsafe_allow_html=True)

                st.markdown("---")
                metrics_row = st.columns(2)
                with metrics_row[0]:
                    st.markdown('<p style="color: rgba(128, 128, 128, 0.8); margin-bottom: 6px;">Predictions Made</p>', unsafe_allow_html=True)
                    st.markdown(f'<p style="color: inherit; font-size: 20px; font-weight: bold; margin-top: -8px; margin-bottom: 0;">{total_predictions}</p>', unsafe_allow_html=True)
                with metrics_row[1]:
                    st.markdown('<p style="color: rgba(128, 128, 128, 0.8); margin-bottom: 6px;">Accurate Predictions</p>', unsafe_allow_html=True)
                    accurate_predictions_value = accurate_predictions if accurate_predictions is not None else "—"
                    delta_value = _format_pct(latest_accuracy) if latest_accuracy is not None else None
                    delta_display = f" ({delta_value})" if delta_value else ""
                    st.markdown(
                        f'<p style="color: inherit; font-size: 20px; font-weight: bold; margin-top: -8px; margin-bottom: 0;">{accurate_predictions_value}'
                        f'<span style="color: green; font-size: 14px;">{delta_display}</span></p>',
                        unsafe_allow_html=True
                    )

    with col2:
        # Evidently Reports accordion with run/view controls
        with st.expander("📊 Evidently Reports", expanded=True):
            st.caption("Generate and open the latest Evidently report.")

            status_text = "No reports generated."
            latest_report = None
            if summary and summary.get("last_report"):
                latest_report = summary.get("last_report", {})
                status_text = "Reports available."

            st.markdown(f"**Status:** {status_text}")

            # Latest report table
            if latest_report:
                report_name = latest_report.get("name")
                created_at = latest_report.get("created_at", "")
                try:
                    # Format to yyyy-mm-dd HH24:mm
                    created_at_display = pd.to_datetime(created_at).strftime("%Y-%m-%d %H:%M")
                except Exception:
                    created_at_display = created_at or "—"

                public_base_url = os.getenv("PUBLIC_APP_BASE_URL", client.base_url)
                report_url = f"{public_base_url.rstrip('/')}/v1/monitoring/reports/{report_name}"

                report_df = pd.DataFrame(
                    [{
                        "Report Name": report_name or "—",
                        "Created Date": created_at_display,
                        "View": f"[Open]({report_url})"
                    }]
                )
                st.table(report_df)
            else:
                st.info("No reports available yet. Generate one to view here.")

            st.markdown("---")

            # New predictions + Generate button row
            stats_cols = st.columns([0.6, 0.4])
            with stats_cols[0]:
                buffered = new_since_report.get("new_since_last_report", buffer_stats.get("total_records", 0))
                st.markdown('<p style="color: rgba(128, 128, 128, 0.8); margin-bottom: 6px;">New Predictions</p>', unsafe_allow_html=True)
                st.markdown(f'<p style="color: inherit; font-size: 20px; font-weight: bold; margin-top: -8px; margin-bottom: 0;">{buffered}</p>', unsafe_allow_html=True)
            with stats_cols[1]:
                if st.button("🧭 Generate", use_container_width=False, type="primary"):
                    with st.spinner("Triggering report generation..."):
                        try:
                            resp = client.session.post(f"{client.base_url}/v1/monitoring/generate", timeout=90)
                            resp.raise_for_status()
                            st.success("Report generation started.")
                        except Exception as exc:
                            st.error(f"Failed to start report generation: {exc}")

    st.divider()

    # Add View HTML Report link aligned to the right
    st.subheader("Classification Quality")
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
    st.markdown('<p style="color: rgba(128, 128, 128, 0.8); font-size: 1.5rem; font-weight: 600; margin-bottom: 1rem;">Drift signals (latest)</p>', unsafe_allow_html=True)
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

    st.markdown('<p style="color: rgba(128, 128, 128, 0.8); font-size: 1.5rem; font-weight: 600; margin-bottom: 1rem;">Drift Trends Over Time</p>', unsafe_allow_html=True)
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

    st.markdown('<p style="color: rgba(128, 128, 128, 0.8); font-size: 1.5rem; font-weight: 600; margin-bottom: 1rem;">Concept Drift Detection</p>', unsafe_allow_html=True)
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

render_model_performance()
