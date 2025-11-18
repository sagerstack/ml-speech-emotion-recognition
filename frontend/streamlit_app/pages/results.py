import streamlit as st
import sys
import os
import time
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

# Add the utils directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))

from audio_utils import AudioProcessor
from api_client import APIClient


def show_results_page():
    """Display the results and history page"""
    st.title("📊 Results & History")
    st.markdown("---")

    # Initialize session state
    if 'prediction_history' not in st.session_state:
        st.session_state.prediction_history = []

    # Page sections
    tab1, tab2, tab3 = st.tabs(["📈 Current Result", "📋 History", "📊 Analytics"])

    with tab1:
        show_current_result()

    with tab2:
        show_prediction_history()

    with tab3:
        show_analytics()


def show_current_result():
    """Display the most recent prediction result"""
    st.subheader("🎯 Current Prediction Result")

    if 'current_prediction' not in st.session_state:
        st.info("No prediction available yet. Go to the Upload page to analyze an audio file.")
        return

    result = st.session_state.current_prediction

    # Main prediction metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        emotion = result.get('emotion', 'Unknown')
        st.metric("Predicted Emotion", emotion.upper())

    with col2:
        confidence = result.get('confidence', 0)
        st.metric("Confidence", f"{confidence:.1%}")

    with col3:
        processing_time = result.get('processing_time', 0)
        st.metric("Processing Time", f"{processing_time:.2f}s")

    with col4:
        timestamp = result.get('timestamp', time.time())
        st.metric("Time", datetime.fromtimestamp(timestamp).strftime("%H:%M:%S"))

    # Confidence indicator
    confidence_color = {
        'high': '🟢',
        'medium': '🟡',
        'low': '🔴'
    }

    confidence_level = 'high' if confidence >= 0.8 else 'medium' if confidence >= 0.6 else 'low'
    st.markdown(f"### Confidence Level: {confidence_color[confidence_level]} {confidence_level.title()}")

    # Detailed probabilities
    probabilities = result.get('probabilities', {})
    if probabilities:
        st.subheader("📊 Detailed Probabilities")

        # Create bar chart
        fig, ax = plt.subplots(figsize=(10, 6))
        emotions = list(probabilities.keys())
        probs = list(probabilities.values())

        # Color the predicted emotion differently
        colors = ['#1f77b4' if emotion == result.get('emotion') else '#d3d3d3' for emotion in emotions]
        bars = ax.bar(emotions, probs, color=colors)

        ax.set_xlabel('Emotions')
        ax.set_ylabel('Probability')
        ax.set_title('Emotion Classification Probabilities')
        ax.set_ylim(0, 1)

        # Add value labels on bars
        for bar, prob in zip(bars, probs):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                   f'{prob:.3f}', ha='center', va='bottom')

        plt.xticks(rotation=45)
        st.pyplot(fig)

        # Table format
        st.subheader("📋 Probability Table")
        prob_data = []
        for emotion, prob in probabilities.items():
            prob_data.append({
                'Emotion': emotion.capitalize(),
                'Probability': f"{prob:.4f}",
                'Percentage': f"{prob*100:.2f}%",
                'Prediction': '✅' if emotion == result.get('emotion') else ''
            })

        df = pd.DataFrame(prob_data)
        st.dataframe(df, use_container_width=True)

    # Additional metadata
    st.subheader("ℹ️ Additional Information")
    metadata = result.get('metadata', {})

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Model Information:**")
        st.write(f"- Model: {metadata.get('model_name', 'Unknown')}")
        st.write(f"- Version: {metadata.get('model_version', 'Unknown')}")
        st.write(f"- Endpoint: {metadata.get('endpoint', 'Unknown')}")

    with col2:
        st.write("**Processing Details:**")
        st.write(f"- Audio Duration: {metadata.get('audio_duration', 'Unknown')}s")
        st.write(f"- Sample Rate: {metadata.get('sample_rate', 'Unknown')} Hz")
        st.write(f"- File Size: {metadata.get('file_size_mb', 'Unknown')} MB")


def show_prediction_history():
    """Display prediction history"""
    st.subheader("📋 Prediction History")

    if not st.session_state.prediction_history:
        st.info("No predictions yet. Upload and analyze audio files to build your history.")
        return

    # History controls
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        st.write(f"Total Predictions: {len(st.session_state.prediction_history)}")

    with col2:
        if st.button("Clear History", type="secondary"):
            st.session_state.prediction_history = []
            st.rerun()

    with col3:
        search_term = st.text_input("Search by filename", placeholder="Search...")

    # Filter history
    filtered_history = st.session_state.prediction_history
    if search_term:
        filtered_history = [
            item for item in filtered_history
            if search_term.lower() in item.get('filename', '').lower()
        ]

    # Display history table
    history_data = []
    for i, item in enumerate(filtered_history):
        result = item.get('result', {})
        history_data.append({
            '#': i + 1,
            'Filename': item.get('filename', 'Unknown'),
            'Emotion': result.get('emotion', 'Unknown'),
            'Confidence': f"{result.get('confidence', 0):.1%}",
            'Processing Time': f"{result.get('processing_time', 0):.2f}s",
            'Timestamp': datetime.fromtimestamp(item.get('timestamp', time.time())).strftime("%Y-%m-%d %H:%M:%S")
        })

    df = pd.DataFrame(history_data)
    st.dataframe(df, use_container_width=True)

    # Detailed view
    if filtered_history:
        st.subheader("🔍 Detailed View")
        selected_index = st.selectbox(
            "Select a prediction to view details:",
            options=range(len(filtered_history)),
            format_func=lambda i: f"#{i+1} - {filtered_history[i].get('filename', 'Unknown')} - {filtered_history[i].get('result', {}).get('emotion', 'Unknown')}"
        )

        if selected_index is not None:
            selected_item = filtered_history[selected_index]
            display_detailed_result(selected_item)


def display_detailed_result(item):
    """Display detailed result for a selected history item"""
    result = item.get('result', {})

    st.markdown(f"### 📁 File: {item.get('filename', 'Unknown')}")

    # Metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Emotion", result.get('emotion', 'Unknown').upper())

    with col2:
        st.metric("Confidence", f"{result.get('confidence', 0):.1%}")

    with col3:
        st.metric("Processing Time", f"{result.get('processing_time', 0):.2f}s")

    with col4:
        timestamp = item.get('timestamp', time.time())
        st.metric("Date", datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d"))

    # Probabilities
    probabilities = result.get('probabilities', {})
    if probabilities:
        st.write("**Probabilities:**")
        prob_cols = st.columns(min(3, len(probabilities)))
        for i, (emotion, prob) in enumerate(probabilities.items()):
            with prob_cols[i % 3]:
                st.write(f"• {emotion}: {prob:.3f} ({prob*100:.1f}%)")


def show_analytics():
    """Display analytics and statistics"""
    st.subheader("📊 Analytics & Statistics")

    if not st.session_state.prediction_history:
        st.info("No data available for analytics. Make some predictions first!")
        return

    # Extract data for analysis
    emotions = []
    confidences = []
    processing_times = []
    timestamps = []

    for item in st.session_state.prediction_history:
        result = item.get('result', {})
        emotions.append(result.get('emotion', 'Unknown'))
        confidences.append(result.get('confidence', 0))
        processing_times.append(result.get('processing_time', 0))
        timestamps.append(item.get('timestamp', time.time()))

    # Summary statistics
    st.subheader("📈 Summary Statistics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Predictions", len(emotions))
        st.metric("Avg Confidence", f"{pd.Series(confidences).mean():.1%}")

    with col2:
        st.metric("Avg Processing Time", f"{pd.Series(processing_times).mean():.2f}s")
        st.metric("Max Confidence", f"{pd.Series(confidences).max():.1%}")

    with col3:
        st.metric("Unique Emotions", len(set(emotions)))
        st.metric("Min Processing Time", f"{pd.Series(processing_times).min():.2f}s")

    with col4:
        st.metric("First Prediction", datetime.fromtimestamp(min(timestamps)).strftime("%Y-%m-%d"))
        st.metric("Last Prediction", datetime.fromtimestamp(max(timestamps)).strftime("%Y-%m-%d"))

    # Emotion distribution
    st.subheader("🎭 Emotion Distribution")
    emotion_counts = pd.Series(emotions).value_counts()

    col1, col2 = st.columns(2)

    with col1:
        # Bar chart
        fig, ax = plt.subplots(figsize=(8, 5))
        emotion_counts.plot(kind='bar', ax=ax, color='skyblue')
        ax.set_title('Emotion Distribution')
        ax.set_xlabel('Emotion')
        ax.set_ylabel('Count')
        plt.xticks(rotation=45)
        st.pyplot(fig)

    with col2:
        # Pie chart
        fig, ax = plt.subplots(figsize=(8, 5))
        emotion_counts.plot(kind='pie', ax=ax, autopct='%1.1f%%')
        ax.set_title('Emotion Distribution')
        ax.set_ylabel('')
        st.pyplot(fig)

    # Confidence analysis
    st.subheader("🎯 Confidence Analysis")

    col1, col2 = st.columns(2)

    with col1:
        # Confidence histogram
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.hist(confidences, bins=10, color='lightgreen', edgecolor='black')
        ax.set_title('Confidence Distribution')
        ax.set_xlabel('Confidence')
        ax.set_ylabel('Frequency')
        ax.set_xlim(0, 1)
        st.pyplot(fig)

    with col2:
        # Confidence over time
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(timestamps, confidences, 'o-', color='orange')
        ax.set_title('Confidence Over Time')
        ax.set_xlabel('Time')
        ax.set_ylabel('Confidence')
        # Format x-axis to show dates
        ax.xaxis.set_major_formatter(plt.DateFormatter('%m-%d'))
        st.pyplot(fig)

    # Processing time analysis
    st.subheader("⏱️ Processing Time Analysis")

    col1, col2 = st.columns(2)

    with col1:
        # Processing time histogram
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.hist(processing_times, bins=10, color='lightcoral', edgecolor='black')
        ax.set_title('Processing Time Distribution')
        ax.set_xlabel('Processing Time (seconds)')
        ax.set_ylabel('Frequency')
        st.pyplot(fig)

    with col2:
        # Processing time stats
        st.write("**Processing Time Statistics:**")
        st.write(f"- Mean: {pd.Series(processing_times).mean():.2f}s")
        st.write(f"- Median: {pd.Series(processing_times).median():.2f}s")
        st.write(f"- Min: {pd.Series(processing_times).min():.2f}s")
        st.write(f"- Max: {pd.Series(processing_times).max():.2f}s")
        st.write(f"- Std Dev: {pd.Series(processing_times).std():.2f}s")


if __name__ == "__main__":
    show_results_page()