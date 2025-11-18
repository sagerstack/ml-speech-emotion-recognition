# 🎭 Production-Grade Streamlit Application

A comprehensive, production-ready ML Speech Emotion Recognition interface that combines the functionality of both the original Streamlit app and React dashboard into a single, unified platform.

## 🚀 Features

### 🎵 Audio Analysis (Original Features)
- **File Upload**: Support for WAV, MP3, FLAC, M4A formats
- **Real-time Processing**: Audio waveform visualization
- **Emotion Prediction**: ML-powered emotion detection with confidence scores
- **Interactive Results**: Detailed probability breakdowns with charts

### 📊 Dashboard (Migrated from React)
- **System Health Monitoring**: Backend API status, model status, uptime tracking
- **Request Metrics**: Real-time requests/minute, response times, error rates
- **Active Connections**: WebSocket connections monitoring
- **Performance Charts**: Interactive charts using Plotly
  - Request volume over time
  - Response time distribution
  - Emotion prediction distribution
- **Live Predictions Feed**: Real-time prediction history
- **System Activity Logs**: Recent system events and status updates

### ⚙️ Settings & Configuration
- **API Configuration**: Backend URL management, connection testing
- **Model Settings**: Local vs SageMaker endpoint configuration
- **Appearance**: Theme selection, auto-refresh settings
- **Advanced Options**: Debug mode, performance settings, cache management

## 🏗️ Architecture

```
Production Streamlit App (Single UI)
├── 🎵 Audio Analysis Page
│   ├── File Upload & Processing
│   ├── Waveform Visualization
│   └── Emotion Prediction Results
├── 📊 Dashboard Page
│   ├── System Health Monitoring
│   ├── Real-time Metrics
│   ├── Interactive Charts
│   └── Live Activity Feed
└── ⚙️ Settings Page
    ├── API Configuration
    ├── Model Settings
    └── Application Preferences
```

## Requirements

- Python 3.8+
- Streamlit 1.29.0+
- Audio processing libraries (librosa, soundfile)
- FastAPI backend running on localhost:8000

## Installation

1. Navigate to the streamlit directory:
```bash
cd frontend/streamlit_app/
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Ensure the FastAPI backend is running:
```bash
# In the backend directory
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Usage

1. Start the Streamlit application:
```bash
streamlit run app.py
```

2. Open your browser and navigate to `http://localhost:8501`

3. Upload an audio file for emotion analysis

## Application Structure

```
frontend/streamlit_app/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── pages/                # Multi-page application modules
│   ├── upload.py         # Audio upload and analysis page
│   └── results.py        # Results history and analytics page
└── utils/                # Utility modules
    ├── api_client.py     # FastAPI backend client
    └── audio_utils.py    # Audio processing utilities
```

## Features by Page

### Main Page (`app.py`)
- Audio file upload with format validation
- Real-time audio preview
- Emotion prediction with confidence scores
- Basic audio visualization (waveform)
- API connection testing
- Model configuration settings

### Upload Page (`pages/upload.py`)
- Advanced audio upload interface
- Comprehensive audio information display
- Feature extraction visualization
- Multiple audio visualizations:
  - Waveform plot
  - Spectrogram
  - MFCC features
- Detailed audio feature analysis

### Results Page (`pages/results.py`)
- Current prediction results
- Prediction history management
- Analytics and statistics dashboard
- Emotion distribution charts
- Confidence and processing time analysis

## Supported Audio Formats

- **WAV**: Best quality, recommended
- **MP3**: Compressed format
- **FLAC**: Lossless compression
- **M4A**: Apple audio format

## Audio Requirements

- **Duration**: 3-30 seconds (optimal)
- **Sample Rate**: 16kHz or higher
- **Quality**: Clear speech, minimal background noise
- **Size**: Maximum 30MB

## Emotion Categories

The model recognizes the following emotions:
- 😠 **Angry**
- 🤢 **Disgusted**
- 😨 **Fearful**
- 😊 **Happy**
- 😐 **Neutral**
- 😢 **Sad**

## API Integration

The Streamlit app integrates with a FastAPI backend that provides:

- `/predict` - Emotion prediction endpoint
- `/health` - Health check endpoint
- `/model/info` - Model information endpoint

## Configuration

### Backend API Settings
- Default URL: `http://localhost:8000`
- Configurable through the sidebar
- Connection testing available

### Audio Settings
- Maximum duration: 30 seconds (configurable)
- Target sample rate: 16kHz
- Audio normalization applied

### Model Settings
- SageMaker endpoint configuration
- Real-time prediction confidence scores
- Detailed probability breakdowns

## Troubleshooting

### Common Issues

1. **API Connection Failed**
   - Ensure FastAPI backend is running on localhost:8000
   - Check firewall settings
   - Verify API URL in sidebar

2. **Audio Upload Fails**
   - Check file format is supported
   - Verify file size < 30MB
   - Ensure audio duration is reasonable

3. **Prediction Errors**
   - Check backend logs for errors
   - Verify SageMaker endpoint is configured
   - Ensure audio quality is adequate

### Performance Tips

- Use shorter audio clips (5-15 seconds) for faster processing
- Ensure good internet connection for API calls
- Close other applications using audio resources

## Development

### Adding New Features

1. **New Pages**: Add new Python files to the `pages/` directory
2. **Utilities**: Add new utility functions to `utils/` directory
3. **Visualizations**: Extend audio_utils.py with new plot functions

### Customization

- Modify CSS styles in `app.py` for different themes
- Add new audio processing features in `audio_utils.py`
- Extend API client for additional backend endpoints

## Dependencies

- **streamlit**: Web application framework
- **librosa**: Audio processing and analysis
- **soundfile**: Audio file I/O
- **requests**: HTTP client for API calls
- **matplotlib**: Plotting and visualization
- **seaborn**: Statistical visualization
- **pandas**: Data manipulation
- **numpy**: Numerical computing

## License

This application is part of the ML Speech Emotion Recognition project.