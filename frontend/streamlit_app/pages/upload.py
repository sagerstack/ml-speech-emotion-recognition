import streamlit as st
import sys
import os

# Add the utils directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))

from audio_utils import AudioProcessor
from api_client import APIClient


def show_upload_page():
    """Display the audio upload page"""
    st.title("📤 Upload Audio for Analysis")
    st.markdown("---")

    # Initialize processors
    if 'audio_processor' not in st.session_state:
        st.session_state.audio_processor = AudioProcessor()
    if 'api_client' not in st.session_state:
        st.session_state.api_client = APIClient()

    # File upload section
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("🎵 Upload Audio File")

        # File upload
        uploaded_file = st.file_uploader(
            "Choose an audio file",
            type=['wav', 'mp3', 'flac', 'm4a'],
            help="Upload an audio file for emotion analysis. Supported formats: WAV, MP3, FLAC, M4A"
        )

        if uploaded_file is not None:
            # File info
            st.info(f"📁 **File:** {uploaded_file.name}")
            st.info(f"📏 **Size:** {uploaded_file.size / (1024*1024):.2f} MB")

            # Validate file format
            if not st.session_state.audio_processor.validate_file_format(uploaded_file.name):
                st.error("❌ Unsupported file format!")
                return

            # Audio player
            st.subheader("🎧 Audio Preview")
            st.audio(uploaded_file, format=f"audio/{uploaded_file.name.split('.')[-1]}")

            # Get audio info
            audio_info = st.session_state.audio_processor.get_audio_info(uploaded_file)

            if "error" in audio_info:
                st.error(f"❌ Error reading audio: {audio_info['error']}")
            else:
                # Display audio information
                st.subheader("📊 Audio Information")
                col1, col2 = st.columns(2)

                with col1:
                    st.metric("Duration", f"{audio_info['duration']:.2f} seconds")
                    st.metric("Sample Rate", f"{audio_info['sample_rate']} Hz")
                    st.metric("Channels", audio_info['channels'])

                with col2:
                    st.metric("Max Amplitude", f"{audio_info['max_amplitude']:.4f}")
                    st.metric("File Size", f"{audio_info['file_size_mb']:.2f} MB")

                # Check if audio is suitable for analysis
                if audio_info['duration'] > 30:
                    st.warning("⚠️ Audio is longer than 30 seconds. It will be truncated during analysis.")
                elif audio_info['duration'] < 1:
                    st.warning("⚠️ Audio is very short. Results may be less accurate.")

                # Analysis button
                st.markdown("---")
                if st.button("🚀 Analyze Emotion", type="primary", use_container_width=True):
                    with st.spinner("Analyzing emotion..."):
                        try:
                            # Load and process audio
                            audio_data, sample_rate = st.session_state.audio_processor.load_audio(uploaded_file)

                            # Extract features for display
                            features = st.session_state.audio_processor.extract_basic_features(
                                audio_data, sample_rate
                            )

                            # Show basic features
                            st.subheader("🔍 Audio Features")
                            col1, col2, col3 = st.columns(3)

                            with col1:
                                st.metric("Mean Amplitude", f"{features['mean_amplitude']:.4f}")
                                st.metric("Zero Crossing Rate", f"{features['zero_crossing_rate']:.4f}")

                            with col2:
                                st.metric("Spectral Centroid", f"{features['spectral_centroid_mean']:.1f} Hz")
                                st.metric("RMS Energy", f"{features['rms_mean']:.4f}")

                            with col3:
                                st.metric("Spectral Rolloff", f"{features['spectral_rolloff_mean']:.1f} Hz")
                                st.metric("Amplitude Std", f"{features['std_amplitude']:.4f}")

                            # Display visualizations
                            st.subheader("📈 Audio Visualizations")

                            # Waveform
                            st.write("**Waveform**")
                            waveform_fig = st.session_state.audio_processor.display_waveform(
                                audio_data, sample_rate, "Audio Waveform"
                            )
                            st.pyplot(waveform_fig)

                            # Spectrogram
                            st.write("**Spectrogram**")
                            spec_fig = st.session_state.audio_processor.display_spectrogram(
                                audio_data, sample_rate, "Spectrogram"
                            )
                            st.pyplot(spec_fig)

                            # MFCC Features
                            st.write("**MFCC Features**")
                            mfcc_fig = st.session_state.audio_processor.display_mfcc(
                                audio_data, sample_rate, "MFCC Features"
                            )
                            st.pyplot(mfcc_fig)

                            # Make API call for emotion prediction
                            st.subheader("🎯 Emotion Prediction")
                            api_url = st.text_input("API URL", value="http://localhost:8000")

                            if st.button("📡 Get Emotion Prediction", use_container_width=True):
                                with st.spinner("Getting prediction from API..."):
                                    try:
                                        result = st.session_state.api_client.predict_emotion(
                                            uploaded_file,
                                            api_url
                                        )

                                        if result:
                                            st.session_state.current_prediction = result
                                            st.success("✅ Prediction complete!")
                                            st.rerun()
                                        else:
                                            st.error("❌ Failed to get prediction")

                                    except Exception as e:
                                        st.error(f"❌ API Error: {str(e)}")

                        except Exception as e:
                            st.error(f"❌ Error processing audio: {str(e)}")

            # Show prediction results if available
            if 'current_prediction' in st.session_state:
                st.markdown("---")
                st.subheader("🎯 Prediction Results")

                result = st.session_state.current_prediction

                # Main prediction
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Emotion", result.get('emotion', 'Unknown').upper())

                with col2:
                    confidence = result.get('confidence', 0)
                    st.metric("Confidence", f"{confidence:.1%}")

                with col3:
                    processing_time = result.get('processing_time', 0)
                    st.metric("Processing Time", f"{processing_time:.2f}s")

                # Probabilities breakdown
                probabilities = result.get('probabilities', {})
                if probabilities:
                    st.write("**All Probabilities:**")
                    for emotion, prob in probabilities.items():
                        st.write(f"• {emotion}: {prob:.3f} ({prob*100:.1f}%)")

    with col2:
        st.subheader("📋 Instructions")

        st.markdown("""
        ### How to use:
        1. **Upload Audio**: Choose an audio file from your device
        2. **Preview**: Listen to the audio to ensure it's correct
        3. **Analyze**: Click the analyze button to extract features
        4. **Predict**: Get emotion prediction from the API

        ### Supported Formats:
        - **WAV**: Best quality
        - **MP3**: Compressed format
        - **FLAC**: Lossless compression
        - **M4A**: Apple audio format

        ### Recommended Audio:
        - **Duration**: 3-30 seconds
        - **Quality**: Clear speech, minimal background noise
        - **Language**: English (model dependent)
        - **Sample Rate**: 16kHz or higher
        """)

        st.markdown("---")
        st.subheader("⚠️ Tips")
        st.markdown("""
        - Speak clearly and naturally
        - Avoid background noise when possible
        - Keep the audio focused on one speaker
        - Shorter clips (5-15 seconds) work best
        - Ensure good audio quality for better accuracy
        """)


if __name__ == "__main__":
    show_upload_page()