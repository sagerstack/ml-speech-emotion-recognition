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
        height=320,
        template="plotly_dark",
        margin=dict(t=40, r=10, l=10, b=10),
        title={
            'text': "Waveform",
            'x': 0,
            'xanchor': 'left',
            'font': {'size': 18}
        },
    )
    return fig


def heatmap_chart(matrix: np.ndarray, title: str):
    fig = px.imshow(matrix, aspect="auto", color_continuous_scale="Turbo")
    fig.update_layout(
        title={
            'text': title,
            'x': 0,
            'xanchor': 'left',
            'font': {'size': 18}
        },
        height=320,
        margin=dict(t=45, r=10, l=10, b=20),
        template="plotly_dark",
    )
    fig.update_xaxes(showticklabels=False)
    fig.update_yaxes(showticklabels=False)
    return fig


def mel_spectrogram_chart(mel_spectrogram: np.ndarray):
    """
    Create chart for Mel Spectrogram.

    Args:
        mel_spectrogram: numpy array of mel spectrogram values (128 mel bands)

    Returns:
        plotly figure
    """
    fig = px.imshow(mel_spectrogram, aspect="auto", color_continuous_scale="Turbo")
    fig.update_layout(
        title={
            'text': "Mel Spectrogram<br>",
            'x': 0,
            'xanchor': 'left',
            'font': {'size': 18}
        },
        height=320,
        margin=dict(t=45, r=10, l=10, b=20),
        template="plotly_dark",
    )
    fig.update_xaxes(showticklabels=False)
    fig.update_yaxes(showticklabels=False)
    return fig


def mfcc_equalizer_chart(mfcc_values: np.ndarray):
    """
    Create an equalizer-style chart for MFCC coefficients.
    Uses normalized display values for better visualization while preserving
    actual values in tooltips.

    Args:
        mfcc_values: numpy array of 20 MFCC coefficient values

    Returns:
        plotly figure
    """
    # Coefficient labels C1-C20
    coefficients = [f"C{i}" for i in range(1, 21)]

    # Normalize coefficients for better visualization
    # Method: Scale each coefficient by the max absolute value in its group
    # This preserves relative patterns while making all coefficients visible

    normalized_values = mfcc_values.copy()

    # Cap all coefficients at +-20
    # This shows actual values (not normalized) but within a reasonable range
    normalized_values = np.clip(mfcc_values, -20, 20)

    # Color coding by frequency range
    colors = []
    for i in range(20):
        if i < 5:  # C0-C4: Low frequency (blue)
            colors.append('#3b82f6')
        elif i < 13:  # C5-C12: Mid frequency (green)
            colors.append('#10b981')
        else:  # C13-C19: High frequency (yellow)
            colors.append('#f59e0b')

    # Create bar chart with both normalized and actual values
    # Format actual values for display on bars
    text_labels = [f"{val:.2f}" for val in mfcc_values]

    fig = go.Figure(data=[
        go.Bar(
            x=coefficients,
            y=normalized_values,
            marker=dict(
                color=colors,
                line=dict(color='rgba(255, 255, 255, 0.3)', width=1)
            ),
            text=text_labels,  # Show actual values on bars
            textposition='outside',
            textfont=dict(size=9),
            customdata=mfcc_values,  # Store original values before capping
            hovertemplate='<b>%{x}</b><br>Value: %{y:.2f}<br>Original: %{customdata:.2f}<extra></extra>',
        )
    ])

    # Add zero baseline
    fig.add_hline(
        y=0,
        line_dash="dash",
        line_color="rgba(255, 255, 255, 0.5)"
    )

    # Layout
    fig.update_layout(
        title={
            'text': "MFCC Spectrum Equalizer<br><sub>Vocal Tract Configuration Analysis</sub>",
            'x': 0,
            'xanchor': 'left',
            'font': {'size': 18}
        },
        xaxis_title="MFCC Coefficients (C1-C20)",
        yaxis_title="Coefficient Value (capped at ±20)",
        yaxis=dict(range=[-20, 20]),
        height=400,
        margin=dict(l=50, r=50, t=80, b=50),
        template="plotly_white",
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0.02)',
    )

    return fig


def delta_mfcc_chart(delta_values: np.ndarray):
    """
    Create chart for Delta MFCC coefficients (rate of change).

    Args:
        delta_values: numpy array of 20 Delta MFCC coefficient values

    Returns:
        plotly figure
    """
    # Coefficient labels C1-C20
    coefficients = [f"C{i}" for i in range(1, 21)]

    # Determine dynamic range based on data with some padding
    max_abs_val = np.max(np.abs(delta_values))
    # Use at least ±3 for range, but expand if data requires
    y_range_limit = max(3, np.ceil(max_abs_val * 1.3))

    # Cap values for display but preserve originals
    display_values = np.clip(delta_values, -y_range_limit, y_range_limit)

    # Color coding by frequency range
    colors = []
    for i in range(20):
        if i < 5:  # C1-C5: Low frequency (blue)
            colors.append('#3b82f6')
        elif i < 13:  # C6-C13: Mid frequency (green)
            colors.append('#10b981')
        else:  # C14-C20: High frequency (yellow)
            colors.append('#f59e0b')

    # Format actual values for display with conditional decimal places
    text_labels = []
    for val in delta_values:
        if abs(val) >= 10:
            text_labels.append(f"{val:.1f}")
        else:
            text_labels.append(f"{val:.2f}")

    fig = go.Figure(data=[
        go.Bar(
            x=coefficients,
            y=display_values,
            marker=dict(
                color=colors,
                line=dict(color='rgba(255, 255, 255, 0.3)', width=1)
            ),
            text=text_labels,
            textposition='outside',
            textfont=dict(size=10, color='rgba(50, 50, 50, 0.9)'),
            customdata=delta_values,
            hovertemplate='<b>%{x}</b><br>Delta Value: %{customdata:.3f}<extra></extra>',
        )
    ])

    # Add zero baseline
    fig.add_hline(
        y=0,
        line_dash="dash",
        line_color="rgba(150, 150, 150, 0.6)",
        line_width=1.5
    )

    # Layout with dynamic range
    fig.update_layout(
        title={
            'text': "Delta MFCC<br><sub>Rate of Change</sub>",
            'x': 0,
            'xanchor': 'left',
            'font': {'size': 18}
        },
        xaxis_title="Coefficients (C1-C20)",
        yaxis_title="Delta Value",
        yaxis=dict(
            range=[-y_range_limit, y_range_limit],
            gridcolor='rgba(200, 200, 200, 0.3)',
            zeroline=False
        ),
        xaxis=dict(
            gridcolor='rgba(200, 200, 200, 0.2)',
        ),
        height=380,
        margin=dict(l=60, r=40, t=85, b=60),
        template="plotly_white",
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0.02)',
    )

    return fig


def delta2_mfcc_chart(delta2_values: np.ndarray):
    """
    Create chart for Delta-Delta MFCC coefficients (acceleration).

    Args:
        delta2_values: numpy array of 20 Delta-Delta MFCC coefficient values

    Returns:
        plotly figure
    """
    # Coefficient labels C1-C20
    coefficients = [f"C{i}" for i in range(1, 21)]

    # Determine dynamic range based on data with some padding
    max_abs_val = np.max(np.abs(delta2_values))
    # Use at least ±2 for range, but expand if data requires
    y_range_limit = max(2, np.ceil(max_abs_val * 1.3))

    # Cap values for display but preserve originals
    display_values = np.clip(delta2_values, -y_range_limit, y_range_limit)

    # Color coding by frequency range
    colors = []
    for i in range(20):
        if i < 5:  # C1-C5: Low frequency (blue)
            colors.append('#3b82f6')
        elif i < 13:  # C6-C13: Mid frequency (green)
            colors.append('#10b981')
        else:  # C14-C20: High frequency (yellow)
            colors.append('#f59e0b')

    # Format actual values for display with conditional decimal places
    text_labels = []
    for val in delta2_values:
        if abs(val) >= 10:
            text_labels.append(f"{val:.1f}")
        else:
            text_labels.append(f"{val:.2f}")

    fig = go.Figure(data=[
        go.Bar(
            x=coefficients,
            y=display_values,
            marker=dict(
                color=colors,
                line=dict(color='rgba(255, 255, 255, 0.3)', width=1)
            ),
            text=text_labels,
            textposition='outside',
            textfont=dict(size=10, color='rgba(50, 50, 50, 0.9)'),
            customdata=delta2_values,
            hovertemplate='<b>%{x}</b><br>Delta-Delta Value: %{customdata:.3f}<extra></extra>',
        )
    ])

    # Add zero baseline
    fig.add_hline(
        y=0,
        line_dash="dash",
        line_color="rgba(150, 150, 150, 0.6)",
        line_width=1.5
    )

    # Layout with dynamic range
    fig.update_layout(
        title={
            'text': "Delta-Delta MFCC<br><sub>Acceleration</sub>",
            'x': 0,
            'xanchor': 'left',
            'font': {'size': 18}
        },
        xaxis_title="Coefficients (C1-C20)",
        yaxis_title="Delta-Delta Value",
        yaxis=dict(
            range=[-y_range_limit, y_range_limit],
            gridcolor='rgba(200, 200, 200, 0.3)',
            zeroline=False
        ),
        xaxis=dict(
            gridcolor='rgba(200, 200, 200, 0.2)',
        ),
        height=380,
        margin=dict(l=60, r=40, t=85, b=60),
        template="plotly_white",
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0.02)',
    )

    return fig


def chroma_chart(chroma: np.ndarray):
    """
    Create chart for Chroma Features.

    Args:
        chroma: numpy array of 12 chroma feature values

    Returns:
        plotly figure
    """
    # Pitch class labels
    pitch_classes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

    # Average across time
    chroma_mean = np.mean(chroma, axis=1)

    # Create bar chart
    fig = go.Figure(data=[
        go.Bar(
            x=pitch_classes,
            y=chroma_mean,
            marker=dict(
                color='#8b5cf6',
                line=dict(color='rgba(255, 255, 255, 0.3)', width=1)
            ),
            text=[f"{val:.3f}" for val in chroma_mean],
            textposition='outside',
            textfont=dict(size=9),
            hovertemplate='<b>%{x}</b><br>Energy: %{y:.3f}<extra></extra>',
        )
    ])

    # Layout
    fig.update_layout(
        title={
            'text': "Chroma Features<br><sub>Pitch Class Energy</sub>",
            'x': 0,
            'xanchor': 'left',
            'font': {'size': 16}
        },
        xaxis_title="Pitch Classes",
        yaxis_title="Energy",
        height=320,
        margin=dict(l=50, r=50, t=80, b=50),
        template="plotly_white",
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0.02)',
    )

    return fig


def prosodic_pitch_chart(pitch_values: np.ndarray, pitch_times: np.ndarray):
    """
    Create chart for Prosodic Features (Pitch over time).

    Args:
        pitch_values: numpy array of pitch values in Hz
        pitch_times: numpy array of time points in seconds

    Returns:
        plotly figure
    """
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=pitch_times,
            y=pitch_values,
            mode='lines+markers',
            line=dict(color='#10b981', width=2),
            marker=dict(size=4, color='#10b981'),
            hovertemplate='<b>Time: %{x:.2f}s</b><br>Pitch: %{y:.1f} Hz<extra></extra>',
        )
    )

    # Layout
    fig.update_layout(
        title={
            'text': "Prosodic Features (Melody)<br><sub>Pitch (Hz) vs Time</sub>",
            'x': 0,
            'xanchor': 'left',
            'font': {'size': 18}
        },
        xaxis_title="Time (seconds)",
        yaxis_title="Pitch (Hz)",
        height=380,
        margin=dict(l=60, r=40, t=85, b=60),
        template="plotly_white",
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0.02)',
        xaxis=dict(
            gridcolor='rgba(200, 200, 200, 0.2)',
        ),
        yaxis=dict(
            gridcolor='rgba(200, 200, 200, 0.3)',
        ),
    )

    return fig

