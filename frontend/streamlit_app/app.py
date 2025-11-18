import streamlit as st
import sys
import os
import requests
import librosa
import soundfile as sf
import numpy as np
import time
from io import BytesIO
from PIL import Image
import matplotlib.pyplot as plt
import seaborn as sns

# Load environment variables from .env.local if it exists
try:
    from dotenv import load_dotenv
    load_dotenv('.env.local')
except ImportError:
    # dotenv not available, will use environment variables as-is
    pass

# Add the utils directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'components'))

from api_client import APIClient
from audio_utils import AudioProcessor
from dashboard import Dashboard

# Configure page
st.set_page_config(
    page_title="Speech Emotion Recognition",
    page_icon="🎭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .emotion-result {
        font-size: 1.2rem;
        font-weight: bold;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .high-confidence {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .medium-confidence {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
    }
    .low-confidence {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'api_client' not in st.session_state:
    st.session_state.api_client = APIClient()
if 'audio_processor' not in st.session_state:
    st.session_state.audio_processor = AudioProcessor()
if 'prediction_history' not in st.session_state:
    st.session_state.prediction_history = []

# Initialize dashboard
if 'dashboard' not in st.session_state:
    st.session_state.dashboard = Dashboard(st.session_state.api_client)

def main():
    # Enhanced navigation sidebar
    with st.sidebar:
        st.header("🧭 Navigation")

        # Page selection
        page = st.selectbox(
            "Select Page",
            ["🎵 Audio Analysis", "📊 Dashboard", "⚙️ Settings"],
            index=0
        )

        st.markdown("---")

    # Different pages based on selection
    if page == "📊 Dashboard":
        st.session_state.dashboard.render_full_dashboard()
        return
    elif page == "⚙️ Settings":
        render_settings_page()
        return

    # Header for other pages
    st.markdown('<h1 class="main-header">🎭 Speech Emotion Recognition</h1>', unsafe_allow_html=True)
    st.markdown("---")

    # Sidebar for configuration (only for Audio Analysis page)
    with st.sidebar:
        st.header("⚙️ Configuration")

        # API Configuration
        st.subheader("API Settings")
        default_api_url = os.getenv('BACKEND_API_URL', 'http://localhost:8000')
        api_url = st.text_input(
            "Backend API URL",
            value=default_api_url,
            help="URL of the FastAPI backend"
        )

        if st.button("Test API Connection"):
            with st.spinner("Testing connection..."):
                try:
                    # Debug: Show what URL we're testing
                    st.write(f"🔍 Testing URL: {api_url}/health")

                    response = st.session_state.api_client.health_check(api_url)

                    # Debug: Show response details
                    if st.session_state.get('debug_mode', False):
                        st.write("📊 Debug Response:")
                        st.json(response)

                    if response.get("status") == "healthy":
                        st.success("✅ API connection successful!")
                        st.write(f"📡 Connected to: {response.get('service', 'Unknown Service')} v{response.get('version', 'Unknown')}")
                    else:
                        st.error("❌ API connection failed")
                        st.write(f"🚫 Status: {response.get('status', 'No response')}")
                        if response.get('message'):
                            st.write(f"💬 Error: {response['message']}")
                except Exception as e:
                    st.error(f"❌ Connection error: {str(e)}")
                    if st.session_state.get('debug_mode', False):
                        st.exception(e)

        st.markdown("---")

        # Model Settings
        st.subheader("Model Settings")
        model_endpoint = st.text_input(
            "SageMaker Endpoint",
            value="test-emotion-endpoint",
            help="AWS SageMaker endpoint name"
        )

        # Audio Settings
        st.subheader("Audio Settings")
        max_duration = st.slider(
            "Max Audio Duration (seconds)",
            min_value=5,
            max_value=60,
            value=30,
            help="Maximum allowed audio duration"
        )

        st.markdown("---")

        # History
        st.subheader("📊 Prediction History")
        if st.session_state.prediction_history:
            st.write(f"Total predictions: {len(st.session_state.prediction_history)}")
            if st.button("Clear History"):
                st.session_state.prediction_history = []
                st.rerun()
        else:
            st.write("No predictions yet")

    # Main content area (only for Audio Analysis)
    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("📤 Upload Audio File")

        # File upload
        uploaded_file = st.file_uploader(
            "Choose an audio file",
            type=['wav', 'mp3', 'flac', 'm4a'],
            help="Supported formats: WAV, MP3, FLAC, M4A"
        )

        if uploaded_file is not None:
            # Display audio info
            st.info(f"📁 File: {uploaded_file.name}")

            # Audio player
            st.audio(uploaded_file, format=f"audio/{uploaded_file.name.split('.')[-1]}")

            # Process audio button
            if st.button("🚀 Analyze Emotion", type="primary"):
                with st.spinner("Processing audio..."):
                    try:
                        # Validate and process audio
                        audio_data, sample_rate = st.session_state.audio_processor.load_audio(uploaded_file)

                        # Display audio waveform
                        st.subheader("📊 Audio Waveform")
                        fig, ax = plt.subplots(figsize=(12, 4))
                        ax.plot(audio_data)
                        ax.set_title("Audio Waveform")
                        ax.set_xlabel("Sample")
                        ax.set_ylabel("Amplitude")
                        st.pyplot(fig)

                        # Get prediction
                        with st.spinner("Analyzing emotion..."):
                            prediction_result = st.session_state.api_client.predict_emotion(
                                uploaded_file,
                                api_url,
                                max_duration
                            )

                        if prediction_result:
                            # Display results
                            display_emotion_results(prediction_result)

                            # Add to history
                            st.session_state.prediction_history.append({
                                'timestamp': time.time(),
                                'filename': uploaded_file.name,
                                'result': prediction_result
                            })
                        else:
                            st.error("❌ Failed to get emotion prediction")

                    except Exception as e:
                        st.error(f"❌ Error processing audio: {str(e)}")

    with col2:
        st.header("📈 Quick Stats")

        # Display statistics
        if st.session_state.prediction_history:
            recent_predictions = st.session_state.prediction_history[-5:]

            st.metric("Total Predictions", len(st.session_state.prediction_history))

            # Emotion distribution
            emotions = [pred['result'].get('emotion', 'Unknown') for pred in recent_predictions]
            emotion_counts = {emotion: emotions.count(emotion) for emotion in set(emotions)}

            if emotion_counts:
                st.subheader("Recent Emotions")
                for emotion, count in emotion_counts.items():
                    st.write(f"• {emotion}: {count}")

        # Model info
        st.markdown("---")
        st.subheader("ℹ️ Model Info")
        st.info("**Supported Emotions:**\n• 😠 Angry\n• 🤢 Disgusted\n• 😨 Fearful\n• 😊 Happy\n• 😐 Neutral\n• 😢 Sad")

        st.info("**Audio Requirements:**\n• Max duration: 30s\n• Sample rate: 16kHz\n• Format: WAV/MP3/FLAC")

def display_emotion_results(result):
    """Display emotion prediction results with confidence"""
    st.header("🎯 Emotion Prediction Results")

    emotion = result.get('emotion', 'Unknown')
    confidence = result.get('confidence', 0)
    probabilities = result.get('probabilities', {})

    # Determine confidence level
    if confidence >= 0.8:
        confidence_class = "high-confidence"
        confidence_text = "High Confidence"
    elif confidence >= 0.6:
        confidence_class = "medium-confidence"
        confidence_text = "Medium Confidence"
    else:
        confidence_class = "low-confidence"
        confidence_text = "Low Confidence"

    # Main prediction result
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        st.metric("Predicted Emotion", emotion.upper())

    with col2:
        st.markdown(f"""
        <div class="emotion-result {confidence_class}">
            <div>{confidence_text}</div>
            <div>Confidence: {confidence:.1%}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.metric("Processing Time", f"{result.get('processing_time', 0):.2f}s")

    # Detailed probabilities
    if probabilities:
        st.subheader("📊 All Emotion Probabilities")

        # Create bar chart
        emotions_list = list(probabilities.keys())
        probs_list = list(probabilities.values())

        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(emotions_list, probs_list)

        # Color code the predicted emotion
        for i, (emotion, prob) in enumerate(zip(emotions_list, probs_list)):
            if emotion == emotion:
                bars[i].set_color('#1f77b4')
            else:
                bars[i].set_color('#lightgray')

        ax.set_xlabel('Emotions')
        ax.set_ylabel('Probability')
        ax.set_title('Emotion Classification Probabilities')
        ax.set_ylim(0, 1)

        # Add value labels on bars
        for bar, prob in zip(bars, probs_list):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{prob:.3f}', ha='center', va='bottom')

        plt.xticks(rotation=45)
        st.pyplot(fig)

        # Also display as table
        st.subheader("📋 Detailed Breakdown")
        prob_df = []
        for emotion, prob in probabilities.items():
            prob_df.append({
                'Emotion': emotion,
                'Probability': f"{prob:.3f}",
                'Percentage': f"{prob*100:.1f}%"
            })

        st.dataframe(prob_df, use_container_width=True)

def render_settings_page():
    """Render application settings and configuration"""
    st.markdown('<h1 class="main-header">⚙️ Settings</h1>', unsafe_allow_html=True)
    st.markdown("---")

    # Configuration sections
    tab1, tab2, tab3 = st.tabs(["🔗 API Settings", "🎨 Appearance", "🧪 Advanced"])

    with tab1:
        st.subheader("🔗 Backend Configuration")

        # API URL configuration
        api_url = st.text_input(
            "Backend API URL",
            value=st.session_state.get('api_url', os.getenv('BACKEND_API_URL', 'http://localhost:8000')),
            help="URL of the FastAPI backend service"
        )
        st.session_state.api_url = api_url

        # Connection test
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🔍 Test Connection"):
                with st.spinner("Testing API connection..."):
                    try:
                        # Debug info
                        st.info(f"🔍 Testing: {api_url}/health")

                        response = st.session_state.api_client.health_check(api_url)

                        # Always show debug info in settings
                        st.write("📊 Response Details:")
                        st.json(response)

                        if response.get("status") == "healthy":
                            st.success("✅ Connection successful!")
                            st.write(f"📡 Service: {response.get('service', 'Unknown')}")
                            st.write(f"🔢 Version: {response.get('version', 'Unknown')}")
                        else:
                            st.error("❌ API returned unhealthy status")
                            if response.get('message'):
                                st.write(f"💬 Error: {response['message']}")
                    except Exception as e:
                        st.error(f"❌ Connection failed: {str(e)}")
                        if st.session_state.get('debug_mode', False):
                            st.exception(e)

        with col2:
            if st.button("🔄 Reset to Default"):
                st.session_state.api_url = os.getenv('BACKEND_API_URL', 'http://localhost:8000')
                st.rerun()

        st.markdown("---")
        st.subheader("🤖 Model Configuration")

        # Model endpoint settings
        sage_endpoint = st.text_input(
            "SageMaker Endpoint Name",
            value=st.session_state.get('sagemaker_endpoint', ''),
            help="AWS SageMaker endpoint for model inference"
        )
        st.session_state.sagemaker_endpoint = sage_endpoint

        # Use local model toggle
        use_local = st.checkbox(
            "Use Local Model",
            value=st.session_state.get('use_local_model', True),
            help="Use local model instead of SageMaker endpoint"
        )
        st.session_state.use_local_model = use_local

    with tab2:
        st.subheader("🎨 Appearance Settings")

        # Theme selection
        theme_option = st.selectbox(
            "Color Theme",
            ["Light", "Dark", "Blue"],
            index=0,
            help="Choose the application color theme"
        )

        # Chart settings
        st.markdown("---")
        st.subheader("📊 Chart Settings")

        auto_refresh = st.checkbox(
            "Enable Auto-refresh",
            value=st.session_state.get('auto_refresh', False),
            help="Automatically refresh dashboard data"
        )
        st.session_state.auto_refresh = auto_refresh

        refresh_interval = st.slider(
            "Refresh Interval (seconds)",
            min_value=10,
            max_value=300,
            value=st.session_state.get('refresh_interval', 30),
            help="How often to refresh dashboard data"
        )
        st.session_state.refresh_interval = refresh_interval

    with tab3:
        st.subheader("🧪 Advanced Configuration")

        # Debug mode
        debug_mode = st.checkbox(
            "Enable Debug Mode",
            value=st.session_state.get('debug_mode', False),
            help="Show additional debugging information"
        )
        st.session_state.debug_mode = debug_mode

        # Performance settings
        st.markdown("---")
        st.subheader("⚡ Performance Settings")

        max_file_size = st.slider(
            "Max File Size (MB)",
            min_value=1,
            max_value=50,
            value=st.session_state.get('max_file_size', 10),
            help="Maximum allowed audio file size"
        )
        st.session_state.max_file_size = max_file_size

        # Cache settings
        st.markdown("---")
        st.subheader("💾 Cache Settings")

        if st.button("🗑️ Clear All Caches"):
            st.cache_data.clear()
            st.success("✅ All caches cleared!")

        if st.button("🔄 Reset Settings"):
            # Reset all session state settings
            keys_to_reset = ['api_url', 'sagemaker_endpoint', 'use_local_model',
                           'auto_refresh', 'refresh_interval', 'debug_mode', 'max_file_size']
            for key in keys_to_reset:
                if key in st.session_state:
                    del st.session_state[key]
            st.success("✅ Settings reset to defaults!")
            st.rerun()

    # Save settings info
    st.markdown("---")
    st.info("💡 **Tip**: Settings are saved in your current session. Reload the page to reset all settings.")

if __name__ == "__main__":
    main()