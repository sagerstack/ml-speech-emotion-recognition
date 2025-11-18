# SageMaker API Usage Guide

This guide provides detailed information on using the deployed SageMaker endpoint for speech emotion recognition.

## Table of Contents

1. [API Overview](#api-overview)
2. [Authentication](#authentication)
3. [Input Formats](#input-formats)
4. [Output Format](#output-format)
5. [Client Libraries](#client-libraries)
6. [Usage Examples](#usage-examples)
7. [Error Handling](#error-handling)
8. [Rate Limiting](#rate-limiting)
9. [Best Practices](#best-practices)

## API Overview

The SageMaker endpoint provides a RESTful API for speech emotion recognition. It accepts audio data in various formats and returns emotion predictions with confidence scores.

### Endpoint Information
- **Model**: ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition
- **Framework**: PyTorch + Transformers
- **Memory**: 2GB
- **Max Concurrency**: 2
- **Timeout**: 60 seconds

### Supported Emotions
The model recognizes 8 emotions:
- happy
- sad
- angry
- neutral
- fearful
- disgusted
- surprised
- calm

## Authentication

### AWS Credentials
The endpoint uses AWS Signature V4 authentication. Configure your AWS credentials:

```bash
aws configure
```

### Environment Variables
```bash
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_REGION="us-east-1"
export SAGEMAKER_ENDPOINT_NAME="your-endpoint-name"
```

### IAM Policy Required
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "sagemaker:InvokeEndpoint"
            ],
            "Resource": "arn:aws:sagemaker:us-east-1:account-id:endpoint/your-endpoint-name"
        }
    ]
}
```

## Input Formats

### 1. JSON with Base64 Audio (Recommended)
```json
{
    "audio_base64": "base64-encoded-audio-data",
    "sample_rate": 16000
}
```

**Headers:**
```
Content-Type: application/json
Accept: application/json
```

### 2. Raw Audio Data
Send raw audio bytes directly to the endpoint.

**Headers:**
```
Content-Type: audio/wav
Accept: application/json
```

### 3. Form Data
```json
{
    "audio_array": [0.1, 0.2, -0.1, ...],
    "sample_rate": 16000
}
```

### Audio Requirements
- **Sample Rate**: 16kHz (recommended), supports 8kHz - 48kHz
- **Channels**: Mono (multi-channel will be mixed to mono)
- **Format**: WAV, MP3, FLAC
- **Duration**: 1-30 seconds (longer audio will be trimmed)
- **Bit Depth**: 16-bit or 32-bit float

## Output Format

### Successful Response
```json
{
    "predicted_emotion": "happy",
    "confidence": 0.892,
    "all_emotions": {
        "happy": 0.892,
        "sad": 0.023,
        "angry": 0.015,
        "neutral": 0.034,
        "fearful": 0.012,
        "disgusted": 0.008,
        "surprised": 0.010,
        "calm": 0.006
    },
    "top_3_emotions": [
        {"emotion": "happy", "score": 0.892},
        {"emotion": "neutral", "score": 0.034},
        {"emotion": "sad", "score": 0.023}
    ],
    "model_info": {
        "model_type": "wav2vec2-lg-xlsr-speech-emotion",
        "num_labels": 8,
        "supported_emotions": ["happy", "sad", "angry", "neutral", "fearful", "disgusted", "surprised", "calm"]
    },
    "invocation_time": 0.234
}
```

### Error Response
```json
{
    "error": "Model timeout error: The model took longer than 60 seconds to process the request",
    "error_type": "ModelTimeoutError",
    "request_id": "12345678-1234-1234-1234-123456789012"
}
```

## Client Libraries

### Python SageMaker Client
The easiest way to use the endpoint is with our Python client:

```python
from sagemaker_client import SageMakerClient

# Initialize client
client = SageMakerClient.from_env()

# Or with config file
client = SageMakerClient.from_config_file("config.yaml", "your-endpoint-name")

# Or manually
from sagemaker_client import SageMakerClient, SageMakerConfig
config = SageMakerConfig(endpoint_name="your-endpoint-name", region="us-east-1")
client = SageMakerClient(config)
```

### JavaScript/Node.js
```javascript
const AWS = require('aws-sdk');
const sagemaker = new AWS.SageMakerRuntime({region: 'us-east-1'});

async function predictEmotion(audioBase64) {
    const params = {
        EndpointName: 'your-endpoint-name',
        ContentType: 'application/json',
        Accept: 'application/json',
        Body: JSON.stringify({
            audio_base64: audioBase64,
            sample_rate: 16000
        })
    };

    try {
        const response = await sagemaker.invokeEndpoint(params).promise();
        const result = JSON.parse(response.Body);
        return result;
    } catch (error) {
        console.error('Error invoking endpoint:', error);
        throw error;
    }
}
```

### curl
```bash
# Base64 audio file
AUDIO_BASE64=$(base64 -w 0 audio.wav)

curl -X POST \
  "https://runtime.sagemaker.us-east-1.amazonaws.com/endpoints/your-endpoint-name/invocations" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "Authorization: AWS4-HMAC-SHA256 ..." \
  -d "{
    \"audio_base64\": \"$AUDIO_BASE64\",
    \"sample_rate\": 16000
  }"
```

## Usage Examples

### Python Examples

#### 1. Basic Prediction from File
```python
from sagemaker_client import SageMakerClient

client = SageMakerClient.from_env()
result = client.predict_emotion_from_file("speech.wav")

print(f"Predicted emotion: {result.predicted_emotion}")
print(f"Confidence: {result.confidence:.3f}")
print(f"Processing time: {result.processing_time:.3f}s")
```

#### 2. Batch Processing
```python
import os
from sagemaker_client import SageMakerClient

client = SageMakerClient.from_env()
audio_files = ["file1.wav", "file2.wav", "file3.wav"]

results = client.batch_predict(audio_files)

for i, result in enumerate(results):
    if result.predicted_emotion != "error":
        print(f"{audio_files[i]}: {result.predicted_emotion} ({result.confidence:.3f})")
    else:
        print(f"{audio_files[i]}: Error processing")
```

#### 3. Real-time Processing
```python
import pyaudio
import numpy as np
from sagemaker_client import SageMakerClient

client = SageMakerClient.from_env()

def process_audio_chunk(audio_data):
    # Convert to base64 and predict
    import base64
    import io
    import soundfile as sf

    buffer = io.BytesIO()
    sf.write(buffer, audio_data, 16000, format='WAV')
    buffer.seek(0)
    audio_base64 = base64.b64encode(buffer.read()).decode('utf-8')

    result = client.predict_emotion_from_base64(audio_base64)
    return result

# Real-time audio processing implementation here...
```

#### 4. FastAPI Integration
```python
from fastapi import FastAPI, UploadFile, File, HTTPException
from sagemaker_client import SageMakerClient
import tempfile
import os

app = FastAPI()
client = SageMakerClient.from_env()

@app.post("/predict-emotion")
async def predict_emotion(audio: UploadFile = File(...)):
    # Validate file type
    if not audio.filename.lower().endswith(('.wav', '.mp3', '.flac')):
        raise HTTPException(status_code=400, detail="Unsupported audio format")

    # Save temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
        content = await audio.read()
        tmp_file.write(content)
        tmp_file_path = tmp_file.name

    try:
        # Predict emotion
        result = client.predict_emotion_from_file(tmp_file_path)
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up
        os.unlink(tmp_file_path)

@app.get("/health")
async def health_check():
    try:
        health = client.health_check()
        return health
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

### JavaScript Examples

#### 1. Browser-based Audio Processing
```javascript
async function analyzeAudio(audioFile) {
    // Convert audio file to base64
    const audioBase64 = await fileToBase64(audioFile);

    const response = await fetch('/api/predict-emotion', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            audio_base64: audioBase64,
            sample_rate: 16000
        })
    });

    const result = await response.json();
    return result;
}

function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = () => resolve(reader.result.split(',')[1]);
        reader.onerror = error => reject(error);
    });
}

// Usage
document.getElementById('audioInput').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (file) {
        const result = await analyzeAudio(file);
        console.log('Emotion:', result.predicted_emotion);
        console.log('Confidence:', result.confidence);
    }
});
```

#### 2. Microphone Recording
```javascript
let mediaRecorder;
let audioChunks = [];

async function startRecording() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);

    mediaRecorder.ondataavailable = (event) => {
        audioChunks.push(event.data);
    };

    mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
        const result = await analyzeAudioBlob(audioBlob);
        displayResult(result);
        audioChunks = [];
    };

    mediaRecorder.start();
}

function stopRecording() {
    mediaRecorder.stop();
}

async function analyzeAudioBlob(audioBlob) {
    const audioBase64 = await blobToBase64(audioBlob);

    const response = await fetch('/api/predict-emotion', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            audio_base64: audioBase64,
            sample_rate: 16000
        })
    });

    return await response.json();
}
```

## Error Handling

### Common Error Types

#### 1. Model Timeout Error
```json
{
    "error": "Model timeout error: The model took longer than 60 seconds to process the request",
    "error_type": "ModelTimeoutError"
}
```
**Solution**: Reduce audio length or check endpoint performance.

#### 2. Invalid Input Error
```json
{
    "error": "Invalid input: Audio format not supported",
    "error_type": "ValidationError"
}
```
**Solution**: Ensure audio is in supported format (WAV, MP3, FLAC).

#### 3. Service Unavailable
```json
{
    "error": "Service unavailable: Endpoint is currently updating",
    "error_type": "ServiceUnavailable"
}
```
**Solution**: Wait a few moments and retry.

### Python Error Handling
```python
from sagemaker_client import SageMakerClient, SageMakerClientError

client = SageMakerClient.from_env()

try:
    result = client.predict_emotion_from_file("audio.wav")
    print(f"Success: {result.predicted_emotion}")
except SageMakerClientError as e:
    print(f"SageMaker error: {e}")
except Exception as e:
    print(f"General error: {e}")
```

### JavaScript Error Handling
```javascript
async function analyzeWithRetry(audioFile, maxRetries = 3) {
    for (let i = 0; i < maxRetries; i++) {
        try {
            const result = await analyzeAudio(audioFile);
            return result;
        } catch (error) {
            console.warn(`Attempt ${i + 1} failed:`, error.message);
            if (i === maxRetries - 1) throw error;
            await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
        }
    }
}
```

## Rate Limiting

### Serverless Limits
- **Max Concurrency**: 2 simultaneous requests
- **Request Rate**: Limited by concurrency

### Handling Rate Limits
```python
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

def batch_predict_with_limiting(client, audio_files, max_workers=2):
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(client.predict_emotion_from_file, file): file
            for file in audio_files
        }

        for future in as_completed(future_to_file):
            file = future_to_file[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"Error processing {file}: {e}")

    return results
```

### Exponential Backoff
```python
import time
import random

def predict_with_backoff(client, audio_file, max_retries=3):
    for attempt in range(max_retries):
        try:
            return client.predict_emotion_from_file(audio_file)
        except Exception as e:
            if attempt == max_retries - 1:
                raise

            # Exponential backoff with jitter
            wait_time = (2 ** attempt) + random.uniform(0, 1)
            print(f"Retry in {wait_time:.1f}s...")
            time.sleep(wait_time)
```

## Best Practices

### 1. Audio Preparation
```python
import librosa
import soundfile as sf

def prepare_audio(file_path, target_sr=16000, max_duration=30):
    # Load audio
    audio, sr = librosa.load(file_path, sr=target_sr)

    # Trim or pad to max duration
    max_length = target_sr * max_duration
    if len(audio) > max_length:
        audio = audio[:max_length]

    # Normalize
    if len(audio) > 0:
        audio = audio / np.max(np.abs(audio))

    return audio, sr

# Save processed audio
def save_processed_audio(audio, sr, output_path):
    sf.write(output_path, audio, sr)
```

### 2. Result Validation
```python
def validate_emotion_result(result):
    # Check confidence threshold
    if result.confidence < 0.5:
        return None, "Low confidence"

    # Check for valid emotion
    valid_emotions = ["happy", "sad", "angry", "neutral", "fearful", "disgusted", "surprised", "calm"]
    if result.predicted_emotion not in valid_emotions:
        return None, "Invalid emotion"

    return result, "Valid"
```

### 3. Caching Results
```python
import hashlib
import pickle
from pathlib import Path

class EmotionCache:
    def __init__(self, cache_dir="cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def get_cache_key(self, audio_data):
        return hashlib.md5(audio_data).hexdigest()

    def get(self, audio_data):
        key = self.get_cache_key(audio_data)
        cache_file = self.cache_dir / f"{key}.pkl"

        if cache_file.exists():
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        return None

    def set(self, audio_data, result):
        key = self.get_cache_key(audio_data)
        cache_file = self.cache_dir / f"{key}.pkl"

        with open(cache_file, 'wb') as f:
            pickle.dump(result, f)

# Usage
cache = EmotionCache()

def predict_with_cache(client, audio_file):
    with open(audio_file, 'rb') as f:
        audio_data = f.read()

    # Try cache first
    cached_result = cache.get(audio_data)
    if cached_result:
        print("Cache hit!")
        return cached_result

    # Predict and cache
    result = client.predict_emotion_from_file(audio_file)
    cache.set(audio_data, result)
    return result
```

### 4. Monitoring and Logging
```python
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def monitored_predict(client, audio_file):
    start_time = datetime.now()

    try:
        result = client.predict_emotion_from_file(audio_file)

        # Log successful prediction
        logger.info(f"Prediction successful: {result.predicted_emotion} "
                   f"(confidence: {result.confidence:.3f}, "
                   f"time: {result.processing_time:.3f}s)")

        return result

    except Exception as e:
        # Log error
        logger.error(f"Prediction failed for {audio_file}: {e}")
        raise

    finally:
        # Log timing
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Total request time: {duration:.3f}s")
```

### 5. Performance Optimization
```python
# Use connection pooling for high-volume applications
from botocore.config import Config

config = Config(
    region_name='us-east-1',
    retries={'max_attempts': 3},
    max_pool_connections=10
)

client = SageMakerClient(
    SageMakerConfig(
        endpoint_name="your-endpoint-name",
        region="us-east-1"
    )
)
client.client = boto3.client('sagemaker-runtime', config=config)
```

## Testing

### Unit Tests
```python
import unittest
from unittest.mock import Mock, patch
from sagemaker_client import SageMakerClient

class TestEmotionClient(unittest.TestCase):
    def setUp(self):
        self.client = SageMakerClient.from_env()

    @patch('sagemaker_client.boto3.client')
    def test_predict_emotion_success(self, mock_boto3):
        # Mock response
        mock_response = {
            'Body': Mock()
        }
        mock_response['Body'].read.return_value = json.dumps({
            'predicted_emotion': 'happy',
            'confidence': 0.892,
            'all_emotions': {'happy': 0.892, 'sad': 0.023}
        }).encode()

        mock_runtime = Mock()
        mock_runtime.invoke_endpoint.return_value = mock_response
        mock_boto3.return_value = mock_runtime

        # Test
        result = self.client.predict_emotion_from_base64("fake_base64")

        self.assertEqual(result.predicted_emotion, 'happy')
        self.assertEqual(result.confidence, 0.892)

if __name__ == '__main__':
    unittest.main()
```

### Load Testing
```python
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import time

async def load_test(endpoint_name, num_requests=100, concurrency=2):
    semaphore = asyncio.Semaphore(concurrency)

    async def single_request():
        async with semaphore:
            start_time = time.time()
            try:
                # Make request here
                await asyncio.sleep(0.2)  # Simulate request
                return {"success": True, "time": time.time() - start_time}
            except Exception as e:
                return {"success": False, "error": str(e)}

    tasks = [single_request() for _ in range(num_requests)]
    results = await asyncio.gather(*tasks)

    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    print(f"Successful: {len(successful)}/{num_requests}")
    print(f"Failed: {len(failed)}/{num_requests}")
    print(f"Avg time: {sum(r['time'] for r in successful) / len(successful):.3f}s")

# Run load test
asyncio.run(load_test("your-endpoint-name"))
```

## Support

For additional support:
- Check the [deployment guide](deployment-guide.md)
- Review AWS SageMaker documentation
- Monitor CloudWatch logs for detailed errors
- Test with the provided client library examples