import streamlit as st
from requests.exceptions import RequestException

from api_client import get_api_client


def render_monitoring() -> None:
    st.title("🔍 Evidently Monitoring")
    st.caption("Review backend-side monitoring status and open the Evidently dashboard.")

    client = get_api_client()

    try:
        summary = client.fetch_monitoring_summary()
    except RequestException as exc:
        st.error(f"Unable to reach monitoring API: {exc}")
        return

    dashboard_url = summary.get("dashboard_url")
    if dashboard_url:
        st.success("Evidently dashboard is available.")
        st.link_button("Open Evidently Dashboard", dashboard_url, type="primary")
    else:
        st.info("Set `EVIDENTLY_DASHBOARD_URL` to expose the hosted Evidently UI.")

    buffer_stats = summary.get("buffer", {})
    col1, col2, col3 = st.columns(3)
    col1.metric("Buffered Predictions", buffer_stats.get("total_records", 0))
    col2.metric("Max Records", buffer_stats.get("max_records", 0))
    latest_timestamp = buffer_stats.get("latest_timestamp") or "—"
    col3.metric("Last Seen", latest_timestamp)

    st.divider()
    st.subheader("Latest Report")
    last_report = summary.get("last_report")
    if last_report:
        st.write(f"Report name: **{last_report.get('name')}**")
        report_url = f"{client.base_url}/v1/monitoring/reports/{last_report.get('name')}"
        st.link_button("View HTML Report", report_url)
        metrics_summary = last_report.get("metrics_summary") or {}
        if metrics_summary:
            st.json(metrics_summary)
    else:
        st.info("No reports generated yet. Run a few inferences to populate the buffer.")

    st.divider()
    st.subheader("Raw Summary")
    st.json(summary)


render_monitoring()
