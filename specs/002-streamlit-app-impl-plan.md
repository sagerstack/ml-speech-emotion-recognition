# Implementation Plan: Enhanced Streamlit Speech Emotion Recognition Frontend

**ID:** 002-streamlit-app-impl-plan
**Created:** November 19, 2025
**Status:** Ready for Development
**Related Specs:** 002-streamlit-app-user-story.md
**Priority:** High

## 📋 Executive Summary

This implementation plan details the systematic enhancement of the existing Streamlit application into a production-grade, laboratory-styled frontend for ML Speech Emotion Recognition. The plan spans 5 phases, from foundational design system to AWS EKS deployment readiness, with comprehensive technical specifications for each component.

## 🎯 Technical Architecture Overview

### Current State Analysis
- **Location**: `frontend/streamlit_app/app.py`
- **Dependencies**: Streamlit, librosa, matplotlib, seaborn, requests, soundfile
- **Current Features**: Basic file upload, waveform display, emotion prediction, API integration
- **Architecture**: Single-file Streamlit application with utility modules

### Target Architecture
```
frontend/streamlit_app/
├── app.py                          # Main application controller
├── components/
│   ├── __init__.py
│   ├── dashboard.py               # Existing dashboard (enhanced)
│   ├── visualizer.py              # New: Audio visualization suite
│   ├── recorder.py                # New: Real-time recording interface
│   ├── batch_processor.py         # New: Batch processing component
│   └── model_comparator.py        # New: Model comparison interface
├── utils/
│   ├── __init__.py
│   ├── audio_utils.py             # Enhanced with all visualizations
│   ├── api_client.py              # Enhanced with WebSocket support
│   ├── css_styler.py              # New: CSS injection and styling
│   └── websocket_client.py        # New: WebSocket functionality
├── assets/
│   ├── css/
│   │   ├── laboratory-theme.css   # Main theme CSS
│   │   ├── components.css         # Component-specific styles
│   │   └── animations.css         # Animation definitions
│   └── js/
│       ├── recorder.js            # WebSocket recording client
│       └── visualizer.js          # Client-side visualizations
└── config/
    └── theme_config.py            # Theme configuration management
```

## 🚀 Phase-by-Phase Implementation

### Phase 1: Design System Foundation (Days 1-2)

**Objective**: Establish "Academic Research Laboratory" aesthetic and base infrastructure

#### 1.1 CSS Theme System
**File**: `frontend/streamlit_app/utils/css_styler.py`

```python
import streamlit as st

class LaboratoryThemeStyler:
    """Injects and manages the Academic Research Laboratory theme"""

    def __init__(self):
        self.theme_vars = {
            # Color System
            '--primary-bg': '#1a1a1a',
            '--secondary-bg': '#2a2a2a',
            '--accent-electric-blue': '#00d4ff',
            '--accent-anger': '#ff4757',
            '--accent-happy': '#ffd93d',
            '--accent-sad': '#6c5ce7',
            '--accent-fear': '#00b894',
            '--accent-disgust': '#fdcb6e',
            '--accent-neutral': '#636e72',

            # Typography
            '--font-mono': '"Space Mono", "Courier New", monospace',
            '--font-body': '"Source Sans Pro", -apple-system, sans-serif',
            '--font-data': '"Inter", sans-serif',

            # Spacing
            '--spacing-xs': '0.25rem',
            '--spacing-sm': '0.5rem',
            '--spacing-md': '1rem',
            '--spacing-lg': '2rem',
            '--spacing-xl': '4rem',

            # Effects
            '--glow-blue': '0 0 20px rgba(0, 212, 255, 0.5)',
            '--shadow-card': '0 8px 32px rgba(0, 0, 0, 0.3)',
            '--border-glow': '1px solid rgba(0, 212, 255, 0.3)'
        }

    def inject_theme(self):
        """Inject the complete laboratory theme CSS"""
        css = self._generate_base_css() + self._generate_component_css()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

    def _generate_base_css(self):
        """Generate base theme CSS"""
        return f"""
        /* Academic Research Laboratory Theme */
        :root {{
            {self._format_css_vars()}
        }}

        /* Override Streamlit defaults */
        .stApp {{
            background: linear-gradient(135deg, var(--primary-bg) 0%, #2d3436 100%);
            color: #ffffff;
        }}

        .main .block-container {{
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1200px;
        }}

        /* Typography */
        h1, h2, h3, h4, h5, h6 {{
            font-family: var(--font-mono);
            font-weight: 600;
            color: var(--accent-electric-blue);
        }}

        p, div, span {{
            font-family: var(--font-body);
        }}

        /* Custom scrollbar */
        ::-webkit-scrollbar {{
            width: 8px;
        }}

        ::-webkit-scrollbar-track {{
            background: var(--secondary-bg);
        }}

        ::-webkit-scrollbar-thumb {{
            background: var(--accent-electric-blue);
            border-radius: 4px;
        }}
        """

    def _format_css_vars(self):
        """Format CSS variables as string"""
        return ';\n'.join([f'{k}: {v}' for k, v in self.theme_vars.items()])
```

#### 1.2 Enhanced Audio Processor
**File**: `frontend/streamlit_app/utils/audio_utils.py` (Enhancement)

```python
class EnhancedAudioProcessor(AudioProcessor):
    """Extended audio processor with comprehensive visualization capabilities"""

    def __init__(self):
        super().__init__()
        self.viz_config = {
            'spectrogram': {
                'colormap': 'viridis',
                'n_fft': 2048,
                'hop_length': 512,
                'title': 'Spectrogram Analysis'
            },
            'mfcc': {
                'n_mfcc': 13,
                'colormap': 'plasma',
                'title': 'MFCC Features'
            },
            'mel_spectrogram': {
                'n_mels': 128,
                'colormap': 'magma',
                'title': 'Mel-Spectrogram'
            },
            'chroma': {
                'n_chroma': 12,
                'colormap': 'coolwarm',
                'title': 'Chroma Features'
            }
        }
        self.setup_matplotlib_theme()

    def setup_matplotlib_theme(self):
        """Configure matplotlib for laboratory aesthetic"""
        plt.style.use('dark_background')
        plt.rcParams.update({
            'figure.facecolor': '#1a1a1a',
            'axes.facecolor': '#2a2a2a',
            'text.color': '#ffffff',
            'axes.labelcolor': '#00d4ff',
            'axes.edgecolor': '#00d4ff',
            'xtick.color': '#ffffff',
            'ytick.color': '#ffffff',
            'font.family': 'Space Mono',
            'font.size': 10
        })

    def display_all_visualizations(self, audio_data, sample_rate):
        """Create comprehensive visualization suite"""
        tabs = st.tabs([
            "🎵 Waveform",
            "📊 Spectrogram",
            "🔬 MFCCs",
            "🌈 Mel-Spectrogram",
            "🎼 Chroma"
        ])

        with tabs[0]:
            self.display_styled_waveform(audio_data, sample_rate)

        with tabs[1]:
            self.display_styled_spectrogram(audio_data, sample_rate)

        with tabs[2]:
            self.display_styled_mfcc(audio_data, sample_rate)

        with tabs[3]:
            self.display_styled_mel_spectrogram(audio_data, sample_rate)

        with tabs[4]:
            self.display_styled_chroma(audio_data, sample_rate)

    def display_styled_spectrogram(self, audio_data, sample_rate):
        """Display spectrogram with laboratory styling"""
        fig, ax = plt.subplots(figsize=(12, 6))

        # Compute spectrogram
        D = librosa.amplitude_to_db(
            np.abs(librosa.stft(audio_data, **self.viz_config['spectrogram'])),
            ref=np.max
        )

        # Create visualization
        img = librosa.display.specshow(
            D,
            sr=sample_rate,
            x_axis='time',
            y_axis='hz',
            ax=ax,
            cmap=self.viz_config['spectrogram']['colormap']
        )

        ax.set_title(self.viz_config['spectrogram']['title'],
                    color='var(--accent-electric-blue)', fontsize=14, fontweight='bold')
        ax.set_xlabel('Time (seconds)', color='#ffffff')
        ax.set_ylabel('Frequency (Hz)', color='#ffffff')

        # Style the plot
        ax.spines['bottom'].set_color('var(--accent-electric-blue)')
        ax.spines['top'].set_color('var(--accent-electric-blue)')
        ax.spines['right'].set_color('var(--accent-electric-blue)')
        ax.spines['left'].set_color('var(--accent-electric-blue)')

        # Add colorbar
        cbar = plt.colorbar(img, ax=ax, format='%+2.0f dB')
        cbar.ax.yaxis.set_tick_params(color='#ffffff')
        plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='#ffffff')

        st.pyplot(fig)
        plt.close()

    def display_styled_mfcc(self, audio_data, sample_rate):
        """Display MFCC features with enhanced styling"""
        fig, ax = plt.subplots(figsize=(12, 6))

        # Compute MFCCs
        mfccs = librosa.feature.mfcc(
            y=audio_data,
            sr=sample_rate,
            n_mfcc=self.viz_config['mfcc']['n_mfcc']
        )

        # Display with custom colormap
        img = librosa.display.specshow(
            mfccs,
            sr=sample_rate,
            x_axis='time',
            ax=ax,
            cmap=self.viz_config['mfcc']['colormap']
        )

        ax.set_title(self.viz_config['mfcc']['title'],
                    color='var(--accent-happy)', fontsize=14, fontweight='bold')
        ax.set_xlabel('Time (seconds)', color='#ffffff')
        ax.set_ylabel('MFCC Coefficients', color='#ffffff')

        # Add grid for scientific look
        ax.grid(True, alpha=0.3, color='var(--accent-electric-blue)')

        # Colorbar
        cbar = plt.colorbar(img, ax=ax, format='%+2.0f')
        cbar.ax.yaxis.set_tick_params(color='#ffffff')
        plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='#ffffff')

        st.pyplot(fig)
        plt.close()

    def display_styled_mel_spectrogram(self, audio_data, sample_rate):
        """Display mel-spectrogram with styling"""
        fig, ax = plt.subplots(figsize=(12, 6))

        # Compute mel-spectrogram
        S = librosa.feature.melspectrogram(
            y=audio_data,
            sr=sample_rate,
            n_mels=self.viz_config['mel_spectrogram']['n_mels']
        )
        S_dB = librosa.power_to_db(S, ref=np.max)

        # Display
        img = librosa.display.specshow(
            S_dB,
            sr=sample_rate,
            x_axis='time',
            y_axis='mel',
            ax=ax,
            cmap=self.viz_config['mel_spectrogram']['colormap']
        )

        ax.set_title(self.viz_config['mel_spectrogram']['title'],
                    color='var(--accent-fear)', fontsize=14, fontweight='bold')
        ax.set_xlabel('Time (seconds)', color='#ffffff')
        ax.set_ylabel('Mel Frequency', color='#ffffff')

        # Colorbar
        cbar = plt.colorbar(img, ax=ax, format='%+2.0f dB')
        cbar.ax.yaxis.set_tick_params(color='#ffffff')
        plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='#ffffff')

        st.pyplot(fig)
        plt.close()

    def display_styled_chroma(self, audio_data, sample_rate):
        """Display chroma features with musical notation style"""
        fig, ax = plt.subplots(figsize=(12, 6))

        # Compute chroma features
        chroma = librosa.feature.chroma_stft(y=audio_data, sr=sample_rate)

        # Display
        img = librosa.display.specshow(
            chroma,
            y_axis='chroma',
            x_axis='time',
            ax=ax,
            cmap=self.viz_config['chroma']['colormap']
        )

        ax.set_title(self.viz_config['chroma']['title'],
                    color='var(--accent-disgust)', fontsize=14, fontweight='bold')
        ax.set_xlabel('Time (seconds)', color='#ffffff')
        ax.set_ylabel('Pitch Class', color='#ffffff')

        # Add musical note labels
        pitch_classes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        ax.set_yticks(range(12))
        ax.set_yticklabels(pitch_classes)

        # Colorbar
        cbar = plt.colorbar(img, ax=ax)
        cbar.ax.yaxis.set_tick_params(color='#ffffff')
        plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='#ffffff')

        st.pyplot(fig)
        plt.close()
```

#### 1.3 Base Integration in Main App
**File**: `frontend/streamlit_app/app.py` (Enhancement)

```python
# Add to imports
from utils.css_styler import LaboratoryThemeStyler
from utils.audio_utils import EnhancedAudioProcessor

# In main() function, after page config:
def apply_laboratory_theme():
    """Apply the Academic Research Laboratory theme"""
    styler = LaboratoryThemeStyler()
    styler.inject_theme()

# Update session state initialization
if 'audio_processor' not in st.session_state:
    st.session_state.audio_processor = EnhancedAudioProcessor()
if 'theme_styler' not in st.session_state:
    st.session_state.theme_styler = LaboratoryThemeStyler()
```

### Phase 2: Real-time Recording Interface (Days 3-4)

**Objective**: Implement WebSocket-based real-time audio recording with laboratory aesthetic

#### 2.1 WebSocket Client Implementation
**File**: `frontend/streamlit_app/utils/websocket_client.py`

```python
import streamlit as st
import websocket
import json
import threading
import time
from typing import Optional, Callable
import base64

class StreamlitWebSocketRecorder:
    """WebSocket-based audio recording client for Streamlit"""

    def __init__(self, backend_url: str = "ws://localhost:8000/ws/audio"):
        self.backend_url = backend_url
        self.recording = False
        self.audio_chunks = []
        self.recording_start_time = None
        self.ws: Optional[websocket.WebSocketApp] = None
        self.recording_thread: Optional[threading.Thread] = None

    def create_websocket_interface(self):
        """Create WebSocket recording interface with JavaScript"""

        js_code = """
        <div id="recording-interface">
            <script>
            let mediaRecorder;
            let audioChunks = [];
            let websocket;
            let recordingStartTime;
            let timerInterval;

            // Initialize WebSocket connection
            function initWebSocket() {
                websocket = new WebSocket('""" + self.backend_url + """');

                websocket.onopen = function(event) {
                    console.log('WebSocket connected for audio recording');
                    updateStatus('connected', 'WebSocket Connected');
                };

                websocket.onclose = function(event) {
                    console.log('WebSocket disconnected');
                    updateStatus('disconnected', 'WebSocket Disconnected');
                };

                websocket.onerror = function(error) {
                    console.error('WebSocket error:', error);
                    updateStatus('error', 'Connection Error');
                };

                websocket.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    if (data.type === 'recording_status') {
                        updateRecordingStatus(data.status);
                    }
                };
            }

            // Start audio recording
            async function startRecording() {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({
                        audio: {
                            sampleRate: 16000,
                            channelCount: 1,
                            echoCancellation: true,
                            noiseSuppression: true
                        }
                    });

                    mediaRecorder = new MediaRecorder(stream, {
                        mimeType: 'audio/webm;codecs=opus'
                    });

                    websocket = new WebSocket('""" + self.backend_url + """');

                    mediaRecorder.ondataavailable = function(event) {
                        if (event.data.size > 0) {
                            audioChunks.push(event.data);
                            // Send chunk to backend
                            if (websocket.readyState === WebSocket.OPEN) {
                                const reader = new FileReader();
                                reader.onload = function() {
                                    const arrayBuffer = reader.result;
                                    websocket.send(JSON.stringify({
                                        type: 'audio_chunk',
                                        data: Array.from(new Uint8Array(arrayBuffer)),
                                        timestamp: Date.now()
                                    }));
                                };
                                reader.readAsArrayBuffer(event.data);
                            }
                        }
                    };

                    mediaRecorder.onstop = function() {
                        // Send recording complete signal
                        if (websocket.readyState === WebSocket.OPEN) {
                            websocket.send(JSON.stringify({
                                type: 'recording_complete',
                                duration: Date.now() - recordingStartTime,
                                total_chunks: audioChunks.length
                            }));
                        }
                    };

                    // Start recording with 100ms chunks
                    mediaRecorder.start(100);
                    recordingStartTime = Date.now();

                    // Start timer
                    startTimer();

                    // Update UI
                    updateStatus('recording', 'Recording...');
                    document.getElementById('start-btn').disabled = true;
                    document.getElementById('stop-btn').disabled = false;

                    // Enable live waveform visualization
                    startLiveWaveform();

                } catch (error) {
                    console.error('Error starting recording:', error);
                    updateStatus('error', 'Microphone access denied');
                }
            }

            // Stop audio recording
            function stopRecording() {
                if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                    mediaRecorder.stop();
                    mediaRecorder.stream.getTracks().forEach(track => track.stop());

                    // Stop timer
                    stopTimer();

                    // Update UI
                    updateStatus('processing', 'Processing...');
                    document.getElementById('start-btn').disabled = false;
                    document.getElementById('stop-btn').disabled = true;

                    // Stop live waveform
                    stopLiveWaveform();
                }
            }

            // Timer functions
            function startTimer() {
                const startTime = Date.now();
                timerInterval = setInterval(function() {
                    const elapsed = Math.floor((Date.now() - startTime) / 1000);
                    const remaining = Math.max(0, 10 - elapsed);
                    updateTimer(remaining, elapsed);

                    if (remaining === 0) {
                        stopRecording();
                    }
                }, 100);
            }

            function stopTimer() {
                if (timerInterval) {
                    clearInterval(timerInterval);
                    timerInterval = null;
                }
            }

            function updateTimer(remaining, elapsed) {
                const timerElement = document.getElementById('timer');
                if (timerElement) {
                    timerElement.textContent = `${remaining}s remaining (${elapsed}s recorded)`;
                }

                // Update progress bar
                const progressBar = document.getElementById('recording-progress');
                if (progressBar) {
                    const progress = (elapsed / 10) * 100;
                    progressBar.style.width = `${Math.min(progress, 100)}%`;
                }
            }

            // Status update functions
            function updateStatus(status, message) {
                const statusElement = document.getElementById('recording-status');
                const lightElement = document.getElementById('recording-light');

                if (statusElement) statusElement.textContent = message;

                if (lightElement) {
                    lightElement.className = 'status-light ' + status;
                }
            }

            // Live waveform visualization
            function startLiveWaveform() {
                // Placeholder for live waveform visualization
                // Will be implemented with Web Audio API
                console.log('Starting live waveform visualization');
            }

            function stopLiveWaveform() {
                console.log('Stopping live waveform visualization');
            }

            // Initialize WebSocket when page loads
            window.addEventListener('load', function() {
                initWebSocket();
            });

            // Expose functions to global scope for Streamlit
            window.startRecording = startRecording;
            window.stopRecording = stopRecording;
            </script>
        </div>
        """

        st.components.v1.html(js_code, height=0)

    def render_recording_interface(self):
        """Render the complete recording interface"""

        st.markdown("""
        <div class="lab-container">
            <h3 style="color: var(--accent-electric-blue); font-family: var(--font-mono);">
                🎤 RECORDING CHAMBER
            </h3>

            <div class="recording-status-bar">
                <div class="status-light" id="recording-light"></div>
                <span id="recording-status" style="font-family: var(--font-mono); color: #ffffff;">
                    Ready to Record
                </span>
            </div>

            <div class="recording-timer">
                <span id="timer" style="font-family: var(--font-mono); color: var(--accent-happy);">
                    10s remaining (0s recorded)
                </span>
            </div>

            <div class="recording-progress-bar">
                <div class="progress-background">
                    <div class="progress-fill" id="recording-progress" style="width: 0%;"></div>
                </div>
            </div>

            <div class="waveform-container" id="live-waveform">
                <canvas id="waveform-canvas" width="800" height="200"></canvas>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Create WebSocket interface
        self.create_websocket_interface()

        # Recording controls
        col1, col2, col3 = st.columns([1, 2, 1])

        with col1:
            if st.button("🔴 START RECORDING", key="start_recording", use_container_width=True):
                st.rerun()  # Trigger rerun to start recording

        with col2:
            # Status display
            if st.session_state.get('recording_status'):
                st.info(f"Status: {st.session_state.recording_status}")

        with col3:
            if st.button("⏹️ STOP RECORDING", key="stop_recording", use_container_width=True):
                st.rerun()  # Trigger rerun to stop recording

        # JavaScript button triggers
        if st.button("Start Recording (JS)", key="js_start"):
            st.components.v1.html("""
            <script>
            if (window.startRecording) {
                window.startRecording();
            }
            </script>
            """, height=0)

        if st.button("Stop Recording (JS)", key="js_stop"):
            st.components.v1.html("""
            <script>
            if (window.stopRecording) {
                window.stopRecording();
            }
            </script>
            """, height=0)
```

#### 2.2 Recording Component Integration
**File**: `frontend/streamlit_app/components/recorder.py`

```python
import streamlit as st
from utils.websocket_client import StreamlitWebSocketRecorder
from utils.css_styler import LaboratoryThemeStyler

class AudioRecorderComponent:
    """Main audio recording component with laboratory styling"""

    def __init__(self):
        self.recorder = StreamlitWebSocketRecorder()
        self.styler = LaboratoryThemeStyler()

    def render(self):
        """Render the complete recording interface"""

        # Inject additional CSS for recording interface
        st.markdown("""
        <style>
        .recording-status-bar {
            display: flex;
            align-items: center;
            margin: 1rem 0;
            padding: 0.75rem;
            background: rgba(42, 42, 42, 0.8);
            border-radius: 8px;
            border: 1px solid rgba(0, 212, 255, 0.2);
        }

        .status-light {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 1rem;
            background: #636e72;
            box-shadow: 0 0 5px rgba(0, 0, 0, 0.5);
            transition: all 0.3s ease;
        }

        .status-light.connected {
            background: #00b894;
            box-shadow: 0 0 10px rgba(0, 184, 148, 0.5);
        }

        .status-light.recording {
            background: #ff4757;
            box-shadow: 0 0 15px rgba(255, 71, 87, 0.7);
            animation: pulse 1s infinite;
        }

        .status-light.processing {
            background: #ffd93d;
            box-shadow: 0 0 10px rgba(255, 217, 61, 0.5);
        }

        .status-light.error {
            background: #d63031;
            box-shadow: 0 0 10px rgba(214, 48, 49, 0.5);
        }

        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }

        .recording-timer {
            text-align: center;
            margin: 1rem 0;
            padding: 0.5rem;
            background: rgba(0, 212, 255, 0.1);
            border-radius: 4px;
            border-left: 4px solid var(--accent-electric-blue);
        }

        .recording-progress-bar {
            margin: 1rem 0;
        }

        .progress-background {
            height: 8px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--accent-electric-blue), var(--accent-happy));
            transition: width 0.1s ease;
            box-shadow: 0 0 10px rgba(0, 212, 255, 0.5);
        }

        .waveform-container {
            margin: 1rem 0;
            padding: 1rem;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 8px;
            border: 1px solid rgba(0, 212, 255, 0.1);
            display: flex;
            justify-content: center;
            align-items: center;
        }

        #waveform-canvas {
            width: 100%;
            height: 200px;
            border-radius: 4px;
        }
        </style>
        """, unsafe_allow_html=True)

        # Render the recording interface
        self.recorder.render_recording_interface()

        # Recording results display
        if st.session_state.get('recording_result'):
            self.display_recording_results()

    def display_recording_results(self):
        """Display results from recording"""
        result = st.session_state.recording_result

        st.markdown("""
        <div class="lab-container">
            <h4 style="color: var(--accent-happy); font-family: var(--font-mono);">
                ✅ Recording Complete
            </h4>
        </div>
        """, unsafe_allow_html=True)

        # Display the audio player
        if 'audio_data' in result:
            st.audio(result['audio_data'], format='audio/wav')

        # Show processing button
        if st.button("🚀 Analyze Recording", type="primary"):
            with st.spinner("Analyzing recorded audio..."):
                # Process the recorded audio
                self.process_recorded_audio(result)

    def process_recorded_audio(self, recording_result):
        """Process the recorded audio through the emotion recognition model"""
        try:
            # Get prediction from API
            prediction = st.session_state.api_client.predict_emotion_from_recording(
                recording_result
            )

            if prediction:
                # Store result and display
                st.session_state.prediction_history.append({
                    'timestamp': time.time(),
                    'filename': 'recording.wav',
                    'type': 'recording',
                    'result': prediction
                })

                # Display results
                from app import display_emotion_results
                display_emotion_results(prediction)

                # Clear recording result
                del st.session_state.recording_result
                st.rerun()
            else:
                st.error("❌ Failed to process recording")

        except Exception as e:
            st.error(f"❌ Error processing recording: {str(e)}")
```

### Phase 3: Batch Processing Interface (Days 5-6)

**Objective**: Implement drag-and-drop batch processing with grid-based results display

#### 3.1 Batch Processing Component
**File**: `frontend/streamlit_app/components/batch_processor.py`

```python
import streamlit as st
import time
from typing import List, Dict, Any
import numpy as np
from utils.audio_utils import EnhancedAudioProcessor
from utils.css_styler import LaboratoryThemeStyler

class BatchProcessorComponent:
    """Batch processing component with drag-and-drop interface"""

    def __init__(self):
        self.audio_processor = EnhancedAudioProcessor()
        self.styler = LaboratoryThemeStyler()

    def render(self):
        """Render the complete batch processing interface"""

        self._inject_batch_processing_css()
        self._render_upload_interface()

        # Process uploaded files
        uploaded_files = st.file_uploader(
            "Select audio files",
            type=['wav', 'mp3', 'flac', 'm4a'],
            accept_multiple_files=True,
            key="batch_upload",
            label_visibility="collapsed"
        )

        if uploaded_files:
            self._display_file_selection(uploaded_files)

            if st.button("🚀 Process Batch", type="primary", use_container_width=True):
                self._process_batch(uploaded_files)

    def _inject_batch_processing_css(self):
        """Inject CSS for batch processing interface"""
        st.markdown("""
        <style>
        .upload-zone {
            border: 2px dashed rgba(0, 212, 255, 0.5);
            border-radius: 12px;
            padding: 3rem 2rem;
            text-align: center;
            background: rgba(42, 42, 42, 0.5);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        .upload-zone:hover {
            border-color: rgba(0, 212, 255, 0.8);
            background: rgba(42, 42, 42, 0.8);
            box-shadow: 0 0 20px rgba(0, 212, 255, 0.2);
        }

        .upload-zone::before {
            content: '';
            position: absolute;
            top: -2px;
            left: -2px;
            right: -2px;
            bottom: -2px;
            background: linear-gradient(45deg, var(--accent-electric-blue), var(--accent-happy));
            border-radius: 12px;
            opacity: 0;
            z-index: -1;
            transition: opacity 0.3s ease;
        }

        .upload-zone:hover::before {
            opacity: 0.3;
        }

        .upload-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
            animation: float 3s ease-in-out infinite;
        }

        @keyframes float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }

        .file-selection-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 1rem;
            margin: 2rem 0;
        }

        .file-card {
            background: rgba(42, 42, 42, 0.8);
            border: 1px solid rgba(0, 212, 255, 0.2);
            border-radius: 8px;
            padding: 1rem;
            transition: all 0.3s ease;
            cursor: pointer;
            position: relative;
        }

        .file-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(0, 212, 255, 0.3);
            border-color: rgba(0, 212, 255, 0.5);
        }

        .file-card.selected {
            background: rgba(0, 212, 255, 0.1);
            border-color: var(--accent-electric-blue);
            box-shadow: 0 0 15px rgba(0, 212, 255, 0.4);
        }

        .file-card.selected::after {
            content: '✓';
            position: absolute;
            top: 0.5rem;
            right: 0.5rem;
            background: var(--accent-electric-blue);
            color: #1a1a1a;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
        }

        .batch-progress {
            margin: 2rem 0;
            padding: 1.5rem;
            background: rgba(42, 42, 42, 0.9);
            border-radius: 8px;
            border: 1px solid rgba(0, 212, 255, 0.2);
        }

        .progress-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }

        .progress-bar {
            height: 8px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 0.5rem;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--accent-electric-blue), var(--accent-happy));
            transition: width 0.3s ease;
            box-shadow: 0 0 10px rgba(0, 212, 255, 0.5);
        }

        .results-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 1.5rem;
            margin: 2rem 0;
        }

        .result-card {
            background: rgba(42, 42, 42, 0.9);
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid rgba(0, 212, 255, 0.2);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        .result-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, var(--accent-electric-blue), var(--accent-happy));
        }

        .result-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 12px 32px rgba(0, 212, 255, 0.3);
        }

        .result-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }

        .result-title {
            font-family: var(--font-mono);
            font-size: 1rem;
            color: #ffffff;
            font-weight: 600;
            margin: 0;
        }

        .emotion-badge {
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.875rem;
            font-weight: 600;
            font-family: var(--font-mono);
        }

        .emotion-angry { background: rgba(255, 71, 87, 0.2); color: #ff4757; border: 1px solid #ff4757; }
        .emotion-happy { background: rgba(255, 217, 61, 0.2); color: #ffd93d; border: 1px solid #ffd93d; }
        .emotion-sad { background: rgba(108, 92, 231, 0.2); color: #6c5ce7; border: 1px solid #6c5ce7; }
        .emotion-fear { background: rgba(0, 184, 148, 0.2); color: #00b894; border: 1px solid #00b894; }
        .emotion-disgust { background: rgba(253, 203, 110, 0.2); color: #fdcb6e; border: 1px solid #fdcb6e; }
        .emotion-neutral { background: rgba(99, 110, 114, 0.2); color: #636e72; border: 1px solid #636e72; }

        .result-metrics {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.5rem;
            margin: 1rem 0;
        }

        .metric-item {
            display: flex;
            justify-content: space-between;
            font-size: 0.875rem;
        }

        .metric-label {
            color: rgba(255, 255, 255, 0.7);
            font-family: var(--font-body);
        }

        .metric-value {
            color: var(--accent-electric-blue);
            font-family: var(--font-mono);
            font-weight: 600;
        }

        .result-actions {
            display: flex;
            gap: 0.5rem;
            margin-top: 1rem;
        }

        .action-button {
            flex: 1;
            padding: 0.5rem;
            background: rgba(0, 212, 255, 0.1);
            border: 1px solid rgba(0, 212, 255, 0.3);
            border-radius: 4px;
            color: var(--accent-electric-blue);
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 0.875rem;
            font-family: var(--font-mono);
        }

        .action-button:hover {
            background: rgba(0, 212, 255, 0.2);
            border-color: var(--accent-electric-blue);
        }
        </style>
        """, unsafe_allow_html=True)

    def _render_upload_interface(self):
        """Render the drag-and-drop upload interface"""
        st.markdown("""
        <div class="lab-container">
            <h3 style="color: var(--accent-electric-blue); font-family: var(--font-mono);">
                📁 BATCH ANALYSIS CHAMBER
            </h3>

            <div class="upload-zone">
                <div class="upload-icon">🎵</div>
                <h4 style="color: #ffffff; font-family: var(--font-mono); margin: 1rem 0;">
                    Drag & Drop Audio Files Here
                </h4>
                <p style="color: rgba(255, 255, 255, 0.7); font-family: var(--font-body); margin: 0.5rem 0;">
                    or click to browse from your computer
                </p>
                <p style="color: rgba(255, 255, 255, 0.5); font-size: 0.875rem; font-family: var(--font-body); margin: 1rem 0 0 0;">
                    Supported formats: WAV, MP3, FLAC, M4A (Max 30MB per file)
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)

    def _display_file_selection(self, uploaded_files: List):
        """Display uploaded files with selection interface"""
        st.markdown('<div class="lab-container">', unsafe_allow_html=True)
        st.markdown('<h4 style="color: var(--accent-electric-blue); font-family: var(--font-mono);">📋 Selected Files</h4>', unsafe_allow_html=True)

        # Initialize selection in session state
        if 'batch_selected_files' not in st.session_state:
            st.session_state.batch_selected_files = {file.name: True for file in uploaded_files}

        # Select all/Deselect all buttons
        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            if st.button("Select All", key="select_all", use_container_width=True):
                st.session_state.batch_selected_files = {file.name: True for file in uploaded_files}
                st.rerun()

        with col2:
            if st.button("Deselect All", key="deselect_all", use_container_width=True):
                st.session_state.batch_selected_files = {file.name: False for file in uploaded_files}
                st.rerun()

        with col3:
            selected_count = sum(st.session_state.batch_selected_files.values())
            st.write(f"Selected: {selected_count}/{len(uploaded_files)} files")

        # File grid display
        st.markdown('<div class="file-selection-grid">', unsafe_allow_html=True)

        for file in uploaded_files:
            is_selected = st.session_state.batch_selected_files.get(file.name, False)

            col1, col2 = st.columns([4, 1])

            with col1:
                # File info display
                file_size_mb = file.size / (1024 * 1024)
                status_class = "selected" if is_selected else ""

                st.markdown(f"""
                <div class="file-card {status_class}" onclick="toggleFileSelection('{file.name}')">
                    <div style="font-family: var(--font-mono); color: #ffffff; font-weight: 600; margin-bottom: 0.5rem;">
                        🎵 {file.name}
                    </div>
                    <div style="font-family: var(--font-body); color: rgba(255, 255, 255, 0.7); font-size: 0.875rem;">
                        Size: {file_size_mb:.1f} MB
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                # Selection checkbox
                new_selection = st.checkbox(
                    "",
                    value=is_selected,
                    key=f"select_{file.name}",
                    label_visibility="collapsed"
                )
                st.session_state.batch_selected_files[file.name] = new_selection

        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # JavaScript for click-to-select functionality
        st.components.v1.html("""
        <script>
        function toggleFileSelection(filename) {
            const checkbox = document.querySelector(`input[key="select_${filename}"]`);
            if (checkbox) {
                checkbox.click();
            }
        }
        </script>
        """, height=0)

    def _process_batch(self, uploaded_files: List):
        """Process the selected batch of files"""

        # Get selected files
        selected_files = [
            file for file in uploaded_files
            if st.session_state.batch_selected_files.get(file.name, False)
        ]

        if not selected_files:
            st.warning("⚠️ No files selected for processing")
            return

        # Initialize batch results
        if 'batch_results' not in st.session_state:
            st.session_state.batch_results = []

        # Create progress container
        progress_container = st.container()

        with progress_container:
            st.markdown('<div class="batch-progress">', unsafe_allow_html=True)
            st.markdown('<div class="progress-header">', unsafe_allow_html=True)
            st.markdown(f'<span>Processing {len(selected_files)} files...</span>', unsafe_allow_html=True)
            st.markdown('<span id="progress-text">0/0</span>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # Progress bar
            progress_bar = st.progress(0)

            st.markdown('<div class="progress-bar">', unsafe_allow_html=True)
            st.markdown('<div class="progress-fill" id="batch-progress-fill" style="width: 0%;"></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

        # Process files
        results = []
        for i, file in enumerate(selected_files):
            try:
                # Update progress
                progress = (i + 1) / len(selected_files)
                progress_bar.progress(progress)

                # Update progress text
                st.components.v1.html(f"""
                <script>
                const progressText = document.getElementById('progress-text');
                const progressFill = document.getElementById('batch-progress-fill');
                if (progressText) progressText.textContent = '{i + 1}/{len(selected_files)}';
                if (progressFill) progressFill.style.width = '{progress * 100}%';
                </script>
                """, height=0)

                # Process the file
                with st.spinner(f"Processing {file.name}..."):
                    # Load and validate audio
                    audio_data, sample_rate = self.audio_processor.load_audio(file)

                    # Get prediction
                    prediction_result = st.session_state.api_client.predict_emotion(
                        file,
                        os.getenv('BACKEND_API_URL', 'http://localhost:8000'),
                        30
                    )

                    if prediction_result:
                        # Store result
                        result = {
                            'filename': file.name,
                            'file_size': file.size,
                            'audio_data': audio_data,
                            'sample_rate': sample_rate,
                            'prediction': prediction_result,
                            'processing_time': prediction_result.get('processing_time', 0),
                            'timestamp': time.time()
                        }
                        results.append(result)

                        # Add to prediction history
                        st.session_state.prediction_history.append({
                            'timestamp': time.time(),
                            'filename': file.name,
                            'type': 'batch',
                            'result': prediction_result
                        })
                    else:
                        # Handle failed prediction
                        results.append({
                            'filename': file.name,
                            'file_size': file.size,
                            'error': 'Failed to process file',
                            'timestamp': time.time()
                        })

            except Exception as e:
                # Handle processing error
                results.append({
                    'filename': file.name,
                    'file_size': file.size,
                    'error': str(e),
                    'timestamp': time.time()
                })

        # Store results and display
        st.session_state.batch_results = results
        st.session_state.show_batch_results = True

        # Clear progress and show success
        st.success(f"✅ Batch processing complete! Processed {len([r for r in results if 'error' not in r])} files successfully.")

        st.rerun()

    def display_results(self):
        """Display batch processing results in a grid layout"""
        if not st.session_state.get('batch_results'):
            return

        results = st.session_state.batch_results

        st.markdown('<div class="lab-container">', unsafe_allow_html=True)
        st.markdown('<h3 style="color: var(--accent-electric-blue); font-family: var(--font-mono);">📊 Batch Analysis Results</h3>', unsafe_allow_html=True)

        # Results summary
        successful_results = [r for r in results if 'error' not in r]
        failed_results = [r for r in results if 'error' in r]

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Files", len(results))

        with col2:
            st.metric("Successful", len(successful_results), delta=f"{len(successful_results)} processed")

        with col3:
            if failed_results:
                st.metric("Failed", len(failed_results), delta=f"-{len(failed_results)} errors")
            else:
                st.metric("Failed", 0, delta="No errors")

        st.markdown('</div>', unsafe_allow_html=True)

        # Results grid
        st.markdown('<div class="results-grid">', unsafe_allow_html=True)

        for result in results:
            self._display_result_card(result)

        st.markdown('</div>', unsafe_allow_html=True)

        # Export options
        self._display_export_options(results)

    def _display_result_card(self, result: Dict[str, Any]):
        """Display a single result card"""

        if 'error' in result:
            # Error card
            st.markdown(f"""
            <div class="result-card">
                <div class="result-header">
                    <h4 class="result-title">❌ {result['filename']}</h4>
                    <span class="emotion-badge" style="background: rgba(214, 48, 49, 0.2); color: #d63031; border: 1px solid #d63031;">
                        ERROR
                    </span>
                </div>
                <p style="color: #d63031; font-family: var(--font-body); margin: 1rem 0;">
                    {result['error']}
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Success card
            prediction = result['prediction']
            emotion = prediction.get('emotion', 'Unknown')
            confidence = prediction.get('confidence', 0)
            processing_time = prediction.get('processing_time', 0)

            emotion_class = emotion.lower().replace(' ', '-')
            emotion_color = self._get_emotion_color(emotion)

            st.markdown(f"""
            <div class="result-card">
                <div class="result-header">
                    <h4 class="result-title">🎵 {result['filename']}</h4>
                    <span class="emotion-badge emotion-{emotion_class}">
                        {emotion.upper()}
                    </span>
                </div>

                <div class="result-metrics">
                    <div class="metric-item">
                        <span class="metric-label">Confidence:</span>
                        <span class="metric-value">{confidence:.1%}</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">Processing:</span>
                        <span class="metric-value">{processing_time:.2f}s</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">File Size:</span>
                        <span class="metric-value">{result['file_size']/(1024*1024):.1f}MB</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">Sample Rate:</span>
                        <span class="metric-value">{result['sample_rate']}Hz</span>
                    </div>
                </div>

                <div class="result-actions">
                    <div class="action-button" onclick="viewDetails('{result['filename']}')">
                        🔍 View Details
                    </div>
                    <div class="action-button" onclick="reprocessFile('{result['filename']}')">
                        🔄 Reprocess
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    def _get_emotion_color(self, emotion: str) -> str:
        """Get color for emotion"""
        emotion_colors = {
            'angry': '#ff4757',
            'happy': '#ffd93d',
            'sad': '#6c5ce7',
            'fear': '#00b894',
            'disgust': '#fdcb6e',
            'neutral': '#636e72'
        }
        return emotion_colors.get(emotion.lower(), '#ffffff')

    def _display_export_options(self, results: List[Dict[str, Any]]):
        """Display export options for batch results"""
        st.markdown('<div class="lab-container">', unsafe_allow_html=True)
        st.markdown('<h4 style="color: var(--accent-electric-blue); font-family: var(--font-mono);">💾 Export Options</h4>', unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("📊 Export as CSV", key="export_csv", use_container_width=True):
                self._export_csv(results)

        with col2:
            if st.button("📄 Export as JSON", key="export_json", use_container_width=True):
                self._export_json(results)

        with col3:
            if st.button("🗑️ Clear Results", key="clear_results", use_container_width=True):
                st.session_state.batch_results = []
                st.session_state.show_batch_results = False
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    def _export_csv(self, results: List[Dict[str, Any]]):
        """Export results as CSV"""
        import pandas as pd
        import io

        # Prepare data
        csv_data = []
        for result in results:
            if 'error' not in result:
                prediction = result['prediction']
                csv_data.append({
                    'filename': result['filename'],
                    'emotion': prediction.get('emotion', ''),
                    'confidence': prediction.get('confidence', 0),
                    'processing_time': prediction.get('processing_time', 0),
                    'file_size_mb': result['file_size'] / (1024 * 1024),
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(result['timestamp']))
                })

        if csv_data:
            df = pd.DataFrame(csv_data)
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)

            st.download_button(
                label="📥 Download CSV",
                data=csv_buffer.getvalue(),
                file_name=f"batch_results_{int(time.time())}.csv",
                mime="text/csv"
            )
        else:
            st.warning("No successful results to export")

    def _export_json(self, results: List[Dict[str, Any]]):
        """Export results as JSON"""
        import json

        # Filter out audio data to reduce file size
        export_data = []
        for result in results:
            export_result = result.copy()
            if 'audio_data' in export_result:
                del export_result['audio_data']
            export_data.append(export_result)

        json_data = json.dumps(export_data, indent=2, default=str)

        st.download_button(
            label="📥 Download JSON",
            data=json_data,
            file_name=f"batch_results_{int(time.time())}.json",
            mime="application/json"
        )
```

### Phase 4: Model Comparison Interface (Days 7-8)

**Objective**: Implement side-by-side model comparison with styled interface

#### 4.1 Model Comparison Component
**File**: `frontend/streamlit_app/components/model_comparator.py`

```python
import streamlit as st
import time
import pandas as pd
from typing import Dict, Any, Optional
from utils.css_styler import LaboratoryThemeStyler
import plotly.graph_objects as go
import plotly.express as px

class ModelComparatorComponent:
    """Model comparison component with side-by-side analysis"""

    def __init__(self):
        self.styler = LaboratoryThemeStyler()

    def render(self):
        """Render the complete model comparison interface"""

        self._inject_comparison_css()

        # Comparison toggle
        comparison_enabled = st.toggle(
            "🔬 ENABLE MODEL COMPARISON",
            value=False,
            help="Compare predictions from Local vs SageMaker models"
        )

        st.session_state.model_comparison_enabled = comparison_enabled

        if comparison_enabled:
            self._render_comparison_interface()
        else:
            self._render_single_model_interface()

    def _inject_comparison_css(self):
        """Inject CSS for model comparison interface"""
        st.markdown("""
        <style>
        .comparison-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
            margin: 2rem 0;
        }

        .model-panel {
            background: rgba(42, 42, 42, 0.9);
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid rgba(0, 212, 255, 0.2);
            position: relative;
            overflow: hidden;
        }

        .model-panel.local {
            border-left: 4px solid var(--accent-happy);
        }

        .model-panel.sagemaker {
            border-left: 4px solid var(--accent-electric-blue);
        }

        .model-header {
            display: flex;
            align-items: center;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }

        .model-icon {
            font-size: 2rem;
            margin-right: 1rem;
        }

        .model-title {
            font-family: var(--font-mono);
            font-size: 1.25rem;
            font-weight: 600;
            margin: 0;
        }

        .model-panel.local .model-title {
            color: var(--accent-happy);
        }

        .model-panel.sagemaker .model-title {
            color: var(--accent-electric-blue);
        }

        .prediction-result {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 8px;
            padding: 1.5rem;
            margin: 1rem 0;
        }

        .emotion-display {
            text-align: center;
            margin: 1.5rem 0;
        }

        .emotion-value {
            font-family: var(--font-mono);
            font-size: 2rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
        }

        .confidence-bar {
            height: 8px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            overflow: hidden;
            margin: 1rem 0;
        }

        .confidence-fill {
            height: 100%;
            transition: width 0.5s ease;
            border-radius: 4px;
        }

        .confidence-fill.high {
            background: linear-gradient(90deg, #00b894, #00d4ff);
        }

        .confidence-fill.medium {
            background: linear-gradient(90deg, #ffd93d, #fdcb6e);
        }

        .confidence-fill.low {
            background: linear-gradient(90deg, #ff4757, #d63031);
        }

        .metrics-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
            margin: 1.5rem 0;
        }

        .metric-card {
            background: rgba(0, 0, 0, 0.2);
            border-radius: 6px;
            padding: 1rem;
            text-align: center;
        }

        .metric-value {
            font-family: var(--font-mono);
            font-size: 1.5rem;
            font-weight: bold;
            color: var(--accent-electric-blue);
        }

        .metric-label {
            font-family: var(--font-body);
            font-size: 0.875rem;
            color: rgba(255, 255, 255, 0.7);
            margin-top: 0.25rem;
        }

        .comparison-summary {
            background: rgba(0, 212, 255, 0.1);
            border: 1px solid rgba(0, 212, 255, 0.3);
            border-radius: 8px;
            padding: 1.5rem;
            margin: 2rem 0;
        }

        .summary-title {
            font-family: var(--font-mono);
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--accent-electric-blue);
            margin-bottom: 1rem;
        }

        .agreement-indicator {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
            font-family: var(--font-mono);
            font-weight: 600;
        }

        .agreement-indicator.agree {
            background: rgba(0, 184, 148, 0.2);
            border: 1px solid #00b894;
            color: #00b894;
        }

        .agreement-indicator.disagree {
            background: rgba(255, 71, 87, 0.2);
            border: 1px solid #ff4757;
            color: #ff4757;
        }

        .probabilities-comparison {
            margin: 2rem 0;
        }

        .chart-container {
            background: rgba(42, 42, 42, 0.9);
            border-radius: 8px;
            padding: 1rem;
            border: 1px solid rgba(0, 212, 255, 0.2);
        }

        @media (max-width: 768px) {
            .comparison-container {
                grid-template-columns: 1fr;
                gap: 1rem;
            }
        }
        </style>
        """, unsafe_allow_html=True)

    def _render_comparison_interface(self):
        """Render the side-by-side comparison interface"""

        st.markdown("""
        <div class="lab-container">
            <h3 style="color: var(--accent-electric-blue); font-family: var(--font-mono);">
                ⚖️ MODEL COMPARISON ARENA
            </h3>
            <p style="color: rgba(255, 255, 255, 0.8); font-family: var(--font-body); margin: 1rem 0;">
                Compare predictions from your local model and AWS SageMaker endpoint side-by-side
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Model endpoint configuration
        self._render_model_configuration()

        # File upload for comparison
        uploaded_file = st.file_uploader(
            "Upload audio file for comparison",
            type=['wav', 'mp3', 'flac', 'm4a'],
            key="comparison_upload"
        )

        if uploaded_file:
            if st.button("🚀 Compare Models", type="primary", use_container_width=True):
                with st.spinner("Running comparison analysis..."):
                    self._run_comparison(uploaded_file)

        # Display comparison results
        if st.session_state.get('comparison_results'):
            self._display_comparison_results()

    def _render_model_configuration(self):
        """Render model configuration panel"""
        with st.expander("⚙️ Model Configuration", expanded=False):
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("🏠 Local Model")
                st.info("Local TensorFlow/PyTorch model running on this machine")

                # Local model settings
                local_model_path = st.text_input(
                    "Model Path",
                    value="models/emotion_model.h5",
                    help="Path to local model file"
                )

                use_gpu = st.checkbox(
                    "Use GPU Acceleration",
                    value=False,
                    help="Use GPU if available for faster inference"
                )

            with col2:
                st.subheader("☁️ SageMaker Model")
                st.info("AWS SageMaker endpoint for cloud-based inference")

                # SageMaker settings
                sagemaker_endpoint = st.text_input(
                    "SageMaker Endpoint",
                    value=st.session_state.get('sagemaker_endpoint', 'test-emotion-endpoint'),
                    help="AWS SageMaker endpoint name"
                )

                aws_region = st.selectbox(
                    "AWS Region",
                    options=['us-east-1', 'us-west-2', 'eu-west-1'],
                    index=0,
                    help="AWS region for SageMaker endpoint"
                )

    def _run_comparison(self, uploaded_file):
        """Run comparison between local and SageMaker models"""

        try:
            # Initialize results
            comparison_results = {
                'filename': uploaded_file.name,
                'timestamp': time.time(),
                'local_model': None,
                'sagemaker_model': None
            }

            # Run local model inference
            with st.spinner("🏠 Running local model inference..."):
                local_result = st.session_state.api_client.predict_emotion(
                    uploaded_file,
                    os.getenv('BACKEND_API_URL', 'http://localhost:8000'),
                    30,
                    model_type='local'
                )
                comparison_results['local_model'] = local_result

            # Run SageMaker model inference
            with st.spinner("☁️ Running SageMaker model inference..."):
                sagemaker_result = st.session_state.api_client.predict_emotion(
                    uploaded_file,
                    os.getenv('BACKEND_API_URL', 'http://localhost:8000'),
                    30,
                    model_type='sagemaker'
                )
                comparison_results['sagemaker_model'] = sagemaker_result

            # Store results
            st.session_state.comparison_results = comparison_results

            # Add to prediction history
            st.session_state.prediction_history.append({
                'timestamp': time.time(),
                'filename': uploaded_file.name,
                'type': 'comparison',
                'result': comparison_results
            })

            st.success("✅ Comparison analysis complete!")
            st.rerun()

        except Exception as e:
            st.error(f"❌ Error running comparison: {str(e)}")

    def _display_comparison_results(self):
        """Display comparison results in side-by-side layout"""

        results = st.session_state.comparison_results

        st.markdown('<div class="comparison-container">', unsafe_allow_html=True)

        # Local Model Panel
        st.markdown('<div class="model-panel local">', unsafe_allow_html=True)
        st.markdown("""
        <div class="model-header">
            <div class="model-icon">🏠</div>
            <h4 class="model-title">LOCAL MODEL</h4>
        </div>
        """, unsafe_allow_html=True)

        if results['local_model']:
            self._display_model_prediction(results['local_model'], 'local')
        else:
            st.error("❌ Local model prediction failed")

        st.markdown('</div>', unsafe_allow_html=True)

        # SageMaker Model Panel
        st.markdown('<div class="model-panel sagemaker">', unsafe_allow_html=True)
        st.markdown("""
        <div class="model-header">
            <div class="model-icon">☁️</div>
            <h4 class="model-title">SAGEMAKER MODEL</h4>
        </div>
        """, unsafe_allow_html=True)

        if results['sagemaker_model']:
            self._display_model_prediction(results['sagemaker_model'], 'sagemaker')
        else:
            st.error("❌ SageMaker model prediction failed")

        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Comparison Summary
        self._display_comparison_summary(results)

        # Probabilities Comparison Chart
        self._display_probabilities_comparison(results)

    def _display_model_prediction(self, prediction: Dict[str, Any], model_type: str):
        """Display prediction result for a single model"""

        emotion = prediction.get('emotion', 'Unknown')
        confidence = prediction.get('confidence', 0)
        processing_time = prediction.get('processing_time', 0)

        st.markdown('<div class="prediction-result">', unsafe_allow_html=True)

        # Emotion display
        st.markdown(f'<div class="emotion-display">', unsafe_allow_html=True)
        st.markdown(f'<div class="emotion-value" style="color: {self._get_emotion_color(emotion)};">{emotion.upper()}</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="color: rgba(255, 255, 255, 0.8);">Predicted Emotion</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Confidence bar
        confidence_class = 'high' if confidence >= 0.8 else 'medium' if confidence >= 0.6 else 'low'
        st.markdown(f'<div class="confidence-bar">', unsafe_allow_html=True)
        st.markdown(f'<div class="confidence-fill {confidence_class}" style="width: {confidence * 100}%;"></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown(f'<div style="text-align: center; margin: 0.5rem 0; font-family: var(--font-mono);">Confidence: {confidence:.1%}</div>', unsafe_allow_html=True)

        # Metrics
        st.markdown('<div class="metrics-grid">', unsafe_allow_html=True)

        st.markdown(f'''
        <div class="metric-card">
            <div class="metric-value">{processing_time:.2f}s</div>
            <div class="metric-label">Processing Time</div>
        </div>
        ''', unsafe_allow_html=True)

        st.markdown(f'''
        <div class="metric-card">
            <div class="metric-value">{prediction.get("model_version", "v1.0")}</div>
            <div class="metric-label">Model Version</div>
        </div>
        ''', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        # Top 3 probabilities
        probabilities = prediction.get('probabilities', {})
        if probabilities:
            top_3 = sorted(probabilities.items(), key=lambda x: x[1], reverse=True)[:3]
            st.markdown('<h5 style="color: var(--accent-electric-blue); font-family: var(--font-mono); margin: 1rem 0 0.5rem 0;">🔝 Top 3 Predictions</h5>', unsafe_allow_html=True)

            for i, (emo, prob) in enumerate(top_3):
                st.markdown(f'''
                <div style="display: flex; justify-content: space-between; align-items: center; margin: 0.5rem 0; padding: 0.5rem; background: rgba(0, 0, 0, 0.2); border-radius: 4px;">
                    <span style="font-family: var(--font-mono); color: {self._get_emotion_color(emo)};">{i+1}. {emo.upper()}</span>
                    <span style="font-family: var(--font-mono); color: var(--accent-electric-blue);">{prob:.1%}</span>
                </div>
                ''', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    def _display_comparison_summary(self, results: Dict[str, Any]):
        """Display comparison summary and agreement analysis"""

        local_result = results['local_model']
        sagemaker_result = results['sagemaker_model']

        if not (local_result and sagemaker_result):
            return

        local_emotion = local_result.get('emotion', '')
        sagemaker_emotion = sagemaker_result.get('emotion', '')
        local_confidence = local_result.get('confidence', 0)
        sagemaker_confidence = sagemaker_result.get('confidence', 0)

        # Check agreement
        emotions_agree = local_emotion.lower() == sagemaker_emotion.lower()
        confidence_diff = abs(local_confidence - sagemaker_confidence)

        st.markdown('<div class="comparison-summary">', unsafe_allow_html=True)
        st.markdown('<div class="summary-title">📊 Comparison Summary</div>', unsafe_allow_html=True)

        # Agreement indicator
        if emotions_agree:
            st.markdown(f'''
            <div class="agreement-indicator agree">
                ✅ MODELS AGREE: Both predicted {local_emotion.upper()}
            </div>
            ''', unsafe_allow_html=True)
        else:
            st.markdown(f'''
            <div class="agreement-indicator disagree">
                ⚠️ MODELS DISAGREE: Local predicted {local_emotion.upper()}, SageMaker predicted {sagemaker_emotion.upper()}
            </div>
            ''', unsafe_allow_html=True)

        # Metrics comparison
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Local Time",
                f"{local_result.get('processing_time', 0):.2f}s",
                delta=f"vs {sagemaker_result.get('processing_time', 0):.2f}s"
            )

        with col2:
            time_improvement = ((sagemaker_result.get('processing_time', 0) - local_result.get('processing_time', 0)) / sagemaker_result.get('processing_time', 1)) * 100
            st.metric("Performance", f"{local_confidence:.1%}", delta=f"{time_improvement:+.1f}%")

        with col3:
            avg_confidence = (local_confidence + sagemaker_confidence) / 2
            st.metric("Avg Confidence", f"{avg_confidence:.1%}")

        with col4:
            confidence_agreement = 100 - (confidence_diff * 100)
            st.metric("Confidence Match", f"{confidence_agreement:.1f}%")

        st.markdown('</div>', unsafe_allow_html=True)

    def _display_probabilities_comparison(self, results: Dict[str, Any]):
        """Display side-by-side probabilities comparison chart"""

        local_result = results['local_model']
        sagemaker_result = results['sagemaker_model']

        if not (local_result and sagemaker_result):
            return

        local_probs = local_result.get('probabilities', {})
        sagemaker_probs = sagemaker_result.get('probabilities', {})

        # Create comparison chart
        emotions = list(set(list(local_probs.keys()) + list(sagemaker_probs.keys())))
        emotions.sort()

        fig = go.Figure()

        # Add local model bars
        local_values = [local_probs.get(emo, 0) for emo in emotions]
        fig.add_trace(go.Bar(
            name='Local Model',
            x=emotions,
            y=local_values,
            marker_color='#ffd93d',
            text=[f'{val:.1%}' for val in local_values],
            textposition='auto',
        ))

        # Add SageMaker model bars
        sagemaker_values = [sagemaker_probs.get(emo, 0) for emo in emotions]
        fig.add_trace(go.Bar(
            name='SageMaker Model',
            x=emotions,
            y=sagemaker_values,
            marker_color='#00d4ff',
            text=[f'{val:.1%}' for val in sagemaker_values],
            textposition='auto',
        ))

        # Update layout
        fig.update_layout(
            title={
                'text': 'Emotion Probabilities Comparison',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'color': '#00d4ff', 'family': 'Space Mono'}
            },
            xaxis_title='Emotions',
            yaxis_title='Probability',
            barmode='group',
            plot_bgcolor='rgba(42, 42, 42, 0.9)',
            paper_bgcolor='rgba(26, 26, 26, 1)',
            font={'color': '#ffffff'},
            xaxis={'tickfont': {'color': '#ffffff'}},
            yaxis={'tickfont': {'color': '#ffffff'}},
            legend={'bgcolor': 'rgba(42, 42, 42, 0.9)', 'bordercolor': '#00d4ff'},
            margin={'l': 50, 'r': 50, 't': 80, 'b': 50}
        )

        st.plotly_chart(fig, use_container_width=True)

    def _render_single_model_interface(self):
        """Render interface when comparison is disabled"""

        st.markdown("""
        <div class="lab-container">
            <h3 style="color: var(--accent-electric-blue); font-family: var(--font-mono);">
                🏠 SINGLE MODEL MODE
            </h3>
            <p style="color: rgba(255, 255, 255, 0.8); font-family: var(--font-body); margin: 1rem 0;">
                Model comparison is disabled. Enable the toggle above to compare predictions from multiple models.
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Show current model settings
        col1, col2 = st.columns(2)

        with col1:
            st.metric("Active Model", "Local")
            st.info("🏠 Using local TensorFlow/PyTorch model")

        with col2:
            st.metric("Comparison Mode", "Disabled")
            st.info("🔄 Enable comparison to see SageMaker results")

    def _get_emotion_color(self, emotion: str) -> str:
        """Get color for emotion"""
        emotion_colors = {
            'angry': '#ff4757',
            'happy': '#ffd93d',
            'sad': '#6c5ce7',
            'fear': '#00b894',
            'disgust': '#fdcb6e',
            'neutral': '#636e72'
        }
        return emotion_colors.get(emotion.lower(), '#ffffff')
```

### Phase 5: Integration and AWS EKS Preparation (Days 9-10)

**Objective**: Complete integration, polish animations, and prepare for AWS EKS deployment

#### 5.1 Enhanced Main App Integration
**File**: `frontend/streamlit_app/app.py` (Major Enhancement)

```python
# Enhanced imports
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

# New component imports
from components.recorder import AudioRecorderComponent
from components.batch_processor import BatchProcessorComponent
from components.model_comparator import ModelComparatorComponent
from utils.css_styler import LaboratoryThemeStyler
from utils.audio_utils import EnhancedAudioProcessor
from utils.api_client import APIClient
from utils.websocket_client import StreamlitWebSocketRecorder

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv('.env.local')
except ImportError:
    pass

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'components'))

# Configure page with enhanced settings
st.set_page_config(
    page_title="Speech Emotion Recognition Laboratory",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

def apply_laboratory_theme():
    """Apply the Academic Research Laboratory theme"""
    styler = LaboratoryThemeStyler()
    styler.inject_theme()

def init_session_state():
    """Initialize enhanced session state"""
    # Enhanced session state variables
    if 'audio_processor' not in st.session_state:
        st.session_state.audio_processor = EnhancedAudioProcessor()
    if 'theme_styler' not in st.session_state:
        st.session_state.theme_styler = LaboratoryThemeStyler()
    if 'api_client' not in st.session_state:
        st.session_state.api_client = APIClient()
    if 'prediction_history' not in st.session_state:
        st.session_state.prediction_history = []
    if 'dashboard' not in st.session_state:
        st.session_state.dashboard = Dashboard(st.session_state.api_client)

    # New session state for advanced features
    if 'batch_results' not in st.session_state:
        st.session_state.batch_results = []
    if 'comparison_results' not in st.session_state:
        st.session_state.comparison_results = None
    if 'model_comparison_enabled' not in st.session_state:
        st.session_state.model_comparison_enabled = False
    if 'recording_result' not in st.session_state:
        st.session_state.recording_result = None
    if 'current_view_mode' not in st.session_state:
        st.session_state.current_view_mode = 'single'

def render_enhanced_sidebar():
    """Render enhanced laboratory-themed sidebar"""
    with st.sidebar:
        # Header with laboratory theme
        st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem; padding: 1rem; background: rgba(0, 212, 255, 0.1); border-radius: 8px; border: 1px solid rgba(0, 212, 255, 0.3);">
            <h2 style="color: var(--accent-electric-blue); font-family: var(--font-mono); margin: 0;">
                🔬 EMOTION LAB
            </h2>
            <p style="color: rgba(255, 255, 255, 0.8); font-family: var(--font-body); margin: 0.5rem 0 0 0;">
                Speech Analysis Platform
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Enhanced navigation
        st.markdown('<h3 style="color: var(--accent-electric-blue); font-family: var(--font-mono); margin-bottom: 1rem;">🧭 Navigation</h3>', unsafe_allow_html=True)

        page = st.selectbox(
            "Select Laboratory Module",
            [
                "🎵 Audio Analysis Chamber",
                "🎤 Recording Studio",
                "📁 Batch Processing",
                "⚖️ Model Comparison",
                "📊 Analytics Dashboard",
                "⚙️ Laboratory Settings"
            ],
            index=0,
            key="navigation_select"
        )

        st.session_state.current_page = page

        st.markdown("---")

        # Quick stats
        st.markdown('<h3 style="color: var(--accent-electric-blue); font-family: var(--font-mono); margin-bottom: 1rem;">📊 Quick Stats</h3>', unsafe_allow_html=True)

        total_predictions = len(st.session_state.prediction_history)
        successful_predictions = len([p for p in st.session_state.prediction_history if p.get('result')])

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total", total_predictions)
        with col2:
            st.metric("Success", successful_predictions)

        # Recent activity
        if st.session_state.prediction_history:
            recent_activity = st.session_state.prediction_history[-5:]
            st.markdown('<h4 style="color: rgba(255, 255, 255, 0.8); font-family: var(--font-mono); margin: 1rem 0 0.5rem 0;">⏰ Recent Activity</h4>', unsafe_allow_html=True)

            for activity in reversed(recent_activity):
                timestamp = activity.get('timestamp', 0)
                time_str = time.strftime('%H:%M:%S', time.localtime(timestamp))
                filename = activity.get('filename', 'Unknown')
                activity_type = activity.get('type', 'upload')

                icon = "🎵" if activity_type == 'upload' else "🎤" if activity_type == 'recording' else "📁" if activity_type == 'batch' else "⚖️"

                st.markdown(f'<div style="font-size: 0.875rem; color: rgba(255, 255, 255, 0.7); margin: 0.25rem 0;">{icon} {time_str} - {filename[:20]}...</div>', unsafe_allow_html=True)

        st.markdown("---")

        # System status
        st.markdown('<h3 style="color: var(--accent-electric-blue); font-family: var(--font-mono); margin-bottom: 1rem;">🔧 System Status</h3>', unsafe_allow_html=True)

        # API connection status
        try:
            api_url = os.getenv('BACKEND_API_URL', 'http://localhost:8000')
            response = st.session_state.api_client.health_check(api_url)

            if response.get("status") == "healthy":
                st.success("✅ API Connected")
                st.info(f"📡 {response.get('service', 'Unknown Service')} v{response.get('version', 'Unknown')}")
            else:
                st.error("❌ API Error")
        except:
            st.error("❌ API Offline")

        # Model comparison status
        if st.session_state.model_comparison_enabled:
            st.success("⚖️ Comparison Mode")
        else:
            st.info("🏠 Single Model Mode")

        # Memory usage indicator
        import psutil
        memory_usage = psutil.virtual_memory().percent
        if memory_usage < 70:
            st.info(f"💾 Memory: {memory_usage:.0f}%")
        else:
            st.warning(f"💾 Memory: {memory_usage:.0f}%")

        st.markdown("---")

        # Laboratory settings shortcut
        if st.button("🔬 Laboratory Settings", use_container_width=True):
            st.session_state.current_page = "⚙️ Laboratory Settings"
            st.rerun()

def main():
    """Enhanced main application controller"""

    # Apply theme and initialize session state
    apply_laboratory_theme()
    init_session_state()

    # Render enhanced sidebar
    render_enhanced_sidebar()

    # Get current page
    current_page = st.session_state.get('current_page', '🎵 Audio Analysis Chamber')

    # Main header
    st.markdown("""
    <div style="text-align: center; margin-bottom: 3rem; padding: 2rem 0;">
        <h1 style="font-size: 3rem; color: var(--accent-electric-blue); font-family: var(--font-mono); font-weight: bold; margin: 0; text-shadow: 0 0 20px rgba(0, 212, 255, 0.5);">
            🔬 SPEECH EMOTION RECOGNITION LABORATORY
        </h1>
        <p style="color: rgba(255, 255, 255, 0.8); font-family: var(--font-body); font-size: 1.2rem; margin: 1rem 0 0 0;">
            Advanced Audio Analysis & Machine Learning Research Platform
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Route to appropriate page
    if current_page == "📊 Analytics Dashboard":
        st.session_state.dashboard.render_full_dashboard()

    elif current_page == "⚙️ Laboratory Settings":
        render_enhanced_settings_page()

    elif current_page == "🎤 Recording Studio":
        render_recording_studio()

    elif current_page == "📁 Batch Processing":
        render_batch_processing_lab()

    elif current_page == "⚖️ Model Comparison":
        render_model_comparison_arena()

    else:  # Default: 🎵 Audio Analysis Chamber
        render_audio_analysis_chamber()

def render_audio_analysis_chamber():
    """Render the main audio analysis interface"""

    st.markdown("""
    <div class="lab-container">
        <h2 style="color: var(--accent-electric-blue); font-family: var(--font-mono);">
            🎵 AUDIO ANALYSIS CHAMBER
        </h2>
        <p style="color: rgba(255, 255, 255, 0.8); font-family: var(--font-body);">
            Upload audio files for comprehensive emotion recognition analysis
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Model comparison toggle
    comparison_component = ModelComparatorComponent()

    # Create main content layout
    col1, col2 = st.columns([3, 1])

    with col1:
        # File upload area
        st.markdown("""
        <div class="lab-container">
            <h3 style="color: var(--accent-electric-blue); font-family: var(--font-mono);">
                📤 SAMPLE UPLOAD
            </h3>
        </div>
        """, unsafe_allow_html=True)

        uploaded_file = st.file_uploader(
            "Choose an audio file",
            type=['wav', 'mp3', 'flac', 'm4a'],
            help="Supported formats: WAV, MP3, FLAC, M4A (Max 30MB)"
        )

        if uploaded_file:
            # Display file info
            file_info = st.session_state.audio_processor.get_audio_info(uploaded_file.getvalue(), uploaded_file.name)

            st.markdown(f"""
            <div style="background: rgba(0, 212, 255, 0.1); border: 1px solid rgba(0, 212, 255, 0.3); border-radius: 8px; padding: 1rem; margin: 1rem 0;">
                <div style="font-family: var(--font-mono); color: var(--accent-electric-blue); font-weight: 600; margin-bottom: 0.5rem;">
                    📁 File Information
                </div>
                <div style="font-family: var(--font-body); color: rgba(255, 255, 255, 0.8);">
                    Duration: {file_info['duration']:.1f}s |
                    Sample Rate: {file_info['sample_rate']}Hz |
                    Size: {file_info['file_size']/(1024*1024):.1f}MB
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Audio player
            st.audio(uploaded_file, format=f"audio/{uploaded_file.name.split('.')[-1]}")

            # Analysis options
            col1a, col1b = st.columns(2)

            with col1a:
                max_duration = st.slider(
                    "Max Duration (seconds)",
                    min_value=5,
                    max_value=30,
                    value=30,
                    help="Maximum audio duration for analysis"
                )

            with col1b:
                include_visualizations = st.checkbox(
                    "Include All Visualizations",
                    value=True,
                    help="Generate spectrograms, MFCCs, and other visualizations"
                )

            # Process button
            if st.button("🚀 Analyze Emotion", type="primary", use_container_width=True):
                with st.spinner("Processing audio..."):
                    try:
                        # Load audio
                        audio_data, sample_rate = st.session_state.audio_processor.load_audio(uploaded_file)

                        # Display visualizations if requested
                        if include_visualizations:
                            st.session_state.audio_processor.display_all_visualizations(audio_data, sample_rate)

                        # Get prediction
                        api_url = os.getenv('BACKEND_API_URL', 'http://localhost:8000')
                        prediction_result = st.session_state.api_client.predict_emotion(
                            uploaded_file, api_url, max_duration
                        )

                        if prediction_result:
                            # Display results
                            display_emotion_results(prediction_result)

                            # Add to history
                            st.session_state.prediction_history.append({
                                'timestamp': time.time(),
                                'filename': uploaded_file.name,
                                'type': 'upload',
                                'result': prediction_result
                            })
                        else:
                            st.error("❌ Failed to get emotion prediction")

                    except Exception as e:
                        st.error(f"❌ Error processing audio: {str(e)}")

    with col2:
        # Quick analysis panel
        st.markdown("""
        <div class="lab-container">
            <h3 style="color: var(--accent-electric-blue); font-family: var(--font-mono);">
                📈 QUICK ANALYSIS
            </h3>
        </div>
        """, unsafe_allow_html=True)

        # Recent predictions summary
        if st.session_state.prediction_history:
            recent_predictions = st.session_state.prediction_history[-10:]

            st.metric("Total Analyses", len(st.session_state.prediction_history))

            # Emotion distribution
            emotions = []
            for pred in recent_predictions:
                if pred.get('result') and pred['result'].get('emotion'):
                    emotions.append(pred['result']['emotion'])

            if emotions:
                emotion_counts = {emotion: emotions.count(emotion) for emotion in set(emotions)}

                st.markdown('<h4 style="color: rgba(255, 255, 255, 0.8); font-family: var(--font-mono); margin: 1rem 0 0.5rem 0;">📊 Recent Emotions</h4>', unsafe_allow_html=True)

                for emotion, count in sorted(emotion_counts.items(), key=lambda x: x[1], reverse=True):
                    emotion_color = comparison_component._get_emotion_color(emotion)
                    st.markdown(f'''
                    <div style="display: flex; justify-content: space-between; align-items: center; margin: 0.5rem 0; padding: 0.5rem; background: rgba(0, 0, 0, 0.2); border-radius: 4px; border-left: 3px solid {emotion_color};">
                        <span style="font-family: var(--font-mono); color: {emotion_color};">{emotion.upper()}</span>
                        <span style="font-family: var(--font-mono); color: var(--accent-electric-blue);">{count}</span>
                    </div>
                    ''', unsafe_allow_html=True)

        # Laboratory info
        st.markdown("---")
        st.markdown("""
        <div class="lab-container">
            <h4 style="color: var(--accent-electric-blue); font-family: var(--font-mono);">
                ℹ️ LABORATORY INFO
            </h4>
            <div style="font-family: var(--font-body); color: rgba(255, 255, 255, 0.8); font-size: 0.875rem;">
                <p><strong>Supported Emotions:</strong></p>
                <ul style="margin: 0.5rem 0;">
                    <li>😠 Angry</li>
                    <li>🤢 Disgusted</li>
                    <li>😨 Fearful</li>
                    <li>😊 Happy</li>
                    <li>😐 Neutral</li>
                    <li>😢 Sad</li>
                </ul>
                <p><strong>Audio Requirements:</strong></p>
                <ul style="margin: 0.5rem 0;">
                    <li>Max duration: 30s</li>
                    <li>Sample rate: 16kHz</li>
                    <li>Format: WAV/MP3/FLAC/M4A</li>
                    <li>Max size: 30MB</li>
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)

def render_recording_studio():
    """Render the recording studio interface"""
    recorder = AudioRecorderComponent()
    recorder.render()

def render_batch_processing_lab():
    """Render the batch processing laboratory"""
    batch_processor = BatchProcessorComponent()

    # Show results if available
    if st.session_state.get('show_batch_results'):
        batch_processor.display_results()
    else:
        batch_processor.render()

def render_model_comparison_arena():
    """Render the model comparison arena"""
    model_comparator = ModelComparatorComponent()
    model_comparator.render()

def render_enhanced_settings_page():
    """Render enhanced laboratory settings page"""
    st.markdown('<h1 class="main-header">⚙️ Laboratory Settings</h1>', unsafe_allow_html=True)
    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs(["🔗 System Configuration", "🎨 Laboratory Theme", "🧊 Performance", "🚀 Deployment"])

    with tab1:
        render_system_configuration()

    with tab2:
        render_theme_settings()

    with tab3:
        render_performance_settings()

    with tab4:
        render_deployment_settings()

def render_system_configuration():
    """Render system configuration settings"""
    st.subheader("🔗 System Configuration")

    # API Configuration
    st.markdown('<h4 style="color: var(--accent-electric-blue); font-family: var(--font-mono);">API Configuration</h4>', unsafe_allow_html=True)

    api_url = st.text_input(
        "Backend API URL",
        value=st.session_state.get('api_url', os.getenv('BACKEND_API_URL', 'http://localhost:8000')),
        help="URL of the FastAPI backend service"
    )
    st.session_state.api_url = api_url

    # Model Configuration
    st.markdown('<h4 style="color: var(--accent-electric-blue); font-family: var(--font-mono);">Model Configuration</h4>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        sage_endpoint = st.text_input(
            "SageMaker Endpoint",
            value=st.session_state.get('sagemaker_endpoint', 'test-emotion-endpoint'),
            help="AWS SageMaker endpoint name"
        )
        st.session_state.sagemaker_endpoint = sage_endpoint

    with col2:
        use_local = st.checkbox(
            "Prefer Local Model",
            value=st.session_state.get('use_local_model', True),
            help="Use local model by default"
        )
        st.session_state.use_local_model = use_local

def render_theme_settings():
    """Render theme customization settings"""
    st.subheader("🎨 Laboratory Theme")

    # Theme options
    st.markdown('<h4 style="color: var(--accent-electric-blue); font-family: var(--font-mono);">Visual Settings</h4>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        theme_variant = st.selectbox(
            "Theme Variant",
            ["Laboratory", "Laboratory Pro", "Minimal"],
            index=0,
            help="Choose the visual theme variant"
        )

        animation_speed = st.slider(
            "Animation Speed",
            min_value=0.5,
            max_value=2.0,
            value=1.0,
            step=0.1,
            help="Speed of interface animations"
        )

    with col2:
        high_contrast = st.checkbox(
            "High Contrast Mode",
            value=False,
            help="Increase contrast for better visibility"
        )

        reduce_motion = st.checkbox(
            "Reduce Motion",
            value=False,
            help="Minimize animations for accessibility"
        )

def render_performance_settings():
    """Render performance optimization settings"""
    st.subheader("🧊 Performance Settings")

    # Audio processing settings
    st.markdown('<h4 style="color: var(--accent-electric-blue); font-family: var(--font-mono);">Audio Processing</h4>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        max_file_size = st.slider(
            "Max File Size (MB)",
            min_value=1,
            max_value=50,
            value=st.session_state.get('max_file_size', 30),
            help="Maximum allowed audio file size"
        )
        st.session_state.max_file_size = max_file_size

    with col2:
        max_duration = st.slider(
            "Max Audio Duration (seconds)",
            min_value=5,
            max_value=60,
            value=st.session_state.get('max_duration', 30),
            help="Maximum allowed audio duration"
        )
        st.session_state.max_duration = max_duration

    # Cache settings
    st.markdown('<h4 style="color: var(--accent-electric-blue); font-family: var(--font-mono);">Cache Management</h4>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🗑️ Clear All Caches", use_container_width=True):
            st.cache_data.clear()
            st.success("✅ All caches cleared!")

    with col2:
        if st.button("🔄 Reset Settings", use_container_width=True):
            keys_to_reset = ['api_url', 'sagemaker_endpoint', 'use_local_model', 'max_file_size', 'max_duration']
            for key in keys_to_reset:
                if key in st.session_state:
                    del st.session_state[key]
            st.success("✅ Settings reset!")
            st.rerun()

def render_deployment_settings():
    """Render deployment configuration settings"""
    st.subheader("🚀 Deployment Configuration")

    # Deployment environment
    st.markdown('<h4 style="color: var(--accent-electric-blue); font-family: var(--font-mono);">Environment</h4>', unsafe_allow_html=True)

    deployment_env = st.selectbox(
        "Deployment Environment",
        ["Local Development", "Docker", "Kubernetes (AWS EKS)"],
        index=0,
        help="Current deployment environment"
    )

    # AWS settings for EKS
    if deployment_env == "Kubernetes (AWS EKS)":
        st.markdown('<h4 style="color: var(--accent-electric-blue); font-family: var(--font-mono);">AWS Configuration</h4>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            aws_region = st.selectbox(
                "AWS Region",
                ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"],
                index=0
            )

            cluster_name = st.text_input(
                "EKS Cluster Name",
                value="ml-emotion-cluster",
                help="Name of the EKS cluster"
            )

        with col2:
            namespace = st.text_input(
                "Kubernetes Namespace",
                value="ml-emotion",
                help="Namespace for deployment"
            )

            service_account = st.text_input(
                "Service Account",
                value="ml-emotion-sa",
                help="Kubernetes service account"
            )

    # Deployment instructions
    st.markdown('<h4 style="color: var(--accent-electric-blue); font-family: var(--font-mono);">Deployment Guide</h4>', unsafe_allow_html=True)

    with st.expander("📚 Deployment Instructions", expanded=False):
        st.markdown("""
        ### Local Development
        ```bash
        cd backend && poetry install && poetry run uvicorn app.main:app --reload
        cd ../frontend/streamlit_app && streamlit run app.py
        ```

        ### Docker Deployment
        ```bash
        docker-compose up -d
        ```

        ### Kubernetes (AWS EKS)
        ```bash
        # Follow deployment-guide-local.md
        cd deployment/k8s
        ./deploy.sh local deploy
        ```
        """)

def display_emotion_results(result):
    """Enhanced emotion results display"""
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

    # Enhanced results display
    st.markdown("""
    <div class="lab-container">
        <h3 style="color: var(--accent-electric-blue); font-family: var(--font-mono);">
            🎯 ANALYSIS RESULTS
        </h3>
    </div>
    """, unsafe_allow_html=True)

    # Main prediction result
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        st.metric("Predicted Emotion", emotion.upper())

    with col2:
        emotion_color = {
            'angry': '#ff4757',
            'happy': '#ffd93d',
            'sad': '#6c5ce7',
            'fear': '#00b894',
            'disgust': '#fdcb6e',
            'neutral': '#636e72'
        }.get(emotion.lower(), '#ffffff')

        st.markdown(f"""
        <div class="emotion-result {confidence_class}" style="border-left: 4px solid {emotion_color};">
            <div style="font-family: var(--font-mono); font-weight: 600;">{confidence_text}</div>
            <div style="font-size: 1.5rem; font-weight: bold; margin: 0.5rem 0;">{confidence:.1%}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.metric("Processing Time", f"{result.get('processing_time', 0):.2f}s")

    # Detailed probabilities
    if probabilities:
        st.markdown("""
        <div class="lab-container">
            <h4 style="color: var(--accent-electric-blue); font-family: var(--font-mono);">
                📊 Emotion Probabilities
            </h4>
        </div>
        """, unsafe_allow_html=True)

        # Create enhanced bar chart
        emotions_list = list(probabilities.keys())
        probs_list = list(probabilities.values())

        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(emotions_list, probs_list)

        # Color code bars
        for i, (emo, prob) in enumerate(zip(emotions_list, probs_list)):
            if emo.lower() == emotion.lower():
                bars[i].set_color('#00d4ff')
                bars[i].set_alpha(1.0)
            else:
                bars[i].set_color('lightgray')
                bars[i].set_alpha(0.6)

        ax.set_xlabel('Emotions', fontsize=12, fontfamily='Space Mono')
        ax.set_ylabel('Probability', fontsize=12, fontfamily='Space Mono')
        ax.set_title('Emotion Classification Probabilities', fontsize=14, fontweight='bold', fontfamily='Space Mono')
        ax.set_ylim(0, 1)

        # Add value labels on bars
        for bar, prob in zip(bars, probs_list):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                   f'{prob:.3f}', ha='center', va='bottom', fontfamily='Space Mono')

        # Style
        ax.spines['bottom'].set_color('#00d4ff')
        ax.spines['top'].set_color('#00d4ff')
        ax.spines['right'].set_color('#00d4ff')
        ax.spines['left'].set_color('#00d4ff')
        ax.tick_params(colors='#ffffff')
        ax.xaxis.label.set_color('#00d4ff')
        ax.yaxis.label.set_color('#00d4ff')
        ax.title.set_color('#00d4ff')

        plt.xticks(rotation=45)
        st.pyplot(fig)
        plt.close()

if __name__ == "__main__":
    main()
```

## 📊 Timeline & Dependencies

### Implementation Timeline
- **Phase 1**: 2 days - Design System Foundation
- **Phase 2**: 2 days - Real-time Recording Interface
- **Phase 3**: 2 days - Batch Processing Interface
- **Phase 4**: 2 days - Model Comparison Interface
- **Phase 5**: 2 days - Integration & AWS EKS Prep

**Total Estimated Time**: 10 days

### Dependencies & Prerequisites

#### Technical Dependencies
1. **Backend API**: FastAPI with WebSocket endpoints
2. **Audio Libraries**: librosa, soundfile, matplotlib, seaborn
3. **Streamlit**: Version 1.28+ for enhanced features
4. **WebSockets**: Browser support and backend implementation
5. **AWS SDK**: Boto3 for SageMaker integration

#### Infrastructure Dependencies
1. **Python 3.11+**: Runtime environment
2. **Node.js**: For any frontend build processes
3. **Docker**: Containerization
4. **Kubernetes**: AWS EKS deployment
5. **AWS Services**: SageMaker, EKS, S3, IAM

### Success Criteria
- [ ] All 5 phases completed successfully
- [ ] Application runs in local development
- [ ] All features work as specified in user story
- [ ] "Academic Research Laboratory" aesthetic implemented consistently
- [ ] Performance requirements met (sub-10s processing, sub-3s load time)
- [ ] Ready for AWS EKS deployment following deployment guide
- [ ] Comprehensive error handling and logging
- [ ] Mobile-responsive design implemented
- [ ] Accessibility requirements met

### Risk Mitigation
1. **Browser Compatibility**: Test WebSocket support across browsers
2. **Performance**: Optimize for large audio files and batch processing
3. **Backend Integration**: Ensure FastAPI endpoints support all new features
4. **AWS Integration**: Test SageMaker connectivity and authentication
5. **User Experience**: Conduct usability testing of complex interfaces

---

**Next Steps**: Upon approval of this implementation plan, begin with Phase 1 (Design System Foundation) and proceed systematically through each phase, ensuring quality and functionality at each step before proceeding to the next.