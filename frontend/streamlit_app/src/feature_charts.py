from typing import Dict

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def probability_bar(probabilities: Dict[str, float], accent: str = "#00d4ff"):
    df = (
        pd.DataFrame(
            {"Emotion": list(probabilities.keys()), "Probability": list(probabilities.values())}
        )
        .sort_values("Probability", ascending=False)
        .reset_index(drop=True)
    )
    fig = px.bar(
        df,
        x="Emotion",
        y="Probability",
        color="Probability",
        color_continuous_scale=[[0, "rgba(148,163,184,0.6)"], [1, accent]],
        text=df["Probability"].map(lambda v: f"{v:.1%}"),
    )
    fig.update_layout(
        height=320,
        template="plotly_dark",
        yaxis=dict(tickformat=".0%"),
        margin=dict(t=50, r=20, l=20, b=30),
    )
    fig.update_traces(textposition="auto")
    return fig


def waveform_chart(waveform: np.ndarray, accent: str = "#00d4ff"):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            y=waveform,
            mode="lines",
            line=dict(color=accent, width=2),
            hoverinfo="skip",
        )
    )
    fig.update_layout(
        height=220,
        template="plotly_dark",
        margin=dict(t=40, r=10, l=10, b=10),
        title="Waveform",
    )
    return fig


def heatmap_chart(matrix: np.ndarray, title: str):
    fig = px.imshow(matrix, aspect="auto", color_continuous_scale="Turbo")
    fig.update_layout(
        title=title,
        height=320,
        margin=dict(t=45, r=10, l=10, b=20),
        template="plotly_dark",
    )
    fig.update_xaxes(showticklabels=False)
    fig.update_yaxes(showticklabels=False)
    return fig

