from datetime import datetime

import pandas as pd
import streamlit as st


def render_history():
    st.title("📜 Analysis History")
    st.caption("Review the latest audio submissions processed through the laboratory pipeline.")

    history = st.session_state.get("codex_iter5_history", [])

    if not history:
        st.info("Run an analysis from the Home page to populate the history log.")
        return

    df = pd.DataFrame(history)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp", ascending=False)
    st.dataframe(
        df.rename(
            columns={
                "timestamp": "Timestamp (UTC)",
                "source": "Source",
                "engine": "Engine",
                "emotion": "Emotion",
                "confidence": "Confidence",
                "processing_time": "Latency (s)",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Recent Timeline")
    for entry in history[:10]:
        stamp = datetime.fromisoformat(entry["timestamp"])
        st.markdown(
            f"- **{entry['emotion'].title()}** ({entry['confidence']:.0%}) via `{entry['engine']}` · "
            f"{stamp.strftime('%Y-%m-%d %H:%M:%S')} UTC · _{entry['source']}_"
        )
