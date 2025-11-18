# SageMaker Model Deployment

This directory contains the deployment scripts and configuration for deploying the speech emotion recognition model to AWS SageMaker serverless endpoints.

## Files Overview

### Core Deployment Files

- **`deploy_model.py`** - Main deployment script with comprehensive deployment management
- **`inference.py`** - SageMaker inference script that runs on the endpoint
- **`config.yaml`** - Deployment configuration file
- **`requirements.txt`** - Model dependencies for SageMaker
- **`validate_model.py`** - Model validation and testing script

### Testing and Integration

- **`test_endpoint.py`** - Comprehensive endpoint testing suite
- **`sagemaker_client.py`** - Python client library for backend integration

### Documentation

- **`../docs/deployment-guide.md`** - Step-by-step deployment instructions
- **`../docs/api-usage.md`** - API usage examples and integration guide
- **`../docs/troubleshooting.md`** - Common issues and solutions

## Quick Start

### 1. Install Dependencies
```bash
cd /Users/sagarpratapsingh/dev/sagerstack/ml-speech-emotion-recognition/sagemaker
poetry install
```

### 2. Validate Model
```bash
cd model-deployment
poetry run python validate_model.py
```

### 3. Deploy Model
```bash
poetry run python deploy_model.py --deploy
```

### 4. Test Deployment
```bash
poetry run python test_endpoint.py <ENDPOINT_NAME> --full
```

## Model Information

- **Model**: `ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition`
- **Framework**: PyTorch + Transformers
- **Memory**: 2GB (serverless)
- **Max Concurrency**: 2
- **Timeout**: 60 seconds
- **Supported Emotions**: 8 emotions (happy, sad, angry, neutral, fearful, disgusted, surprised, calm)

## Configuration

Edit `config.yaml` to customize deployment parameters:

```yaml
# Model Configuration
model:
  name: "ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition"

# Serverless Configuration
serverless:
  memory_size_in_mb: 2048
  max_concurrency: 2
  timeout_in_seconds: 60

# AWS Configuration
aws:
  region: "us-east-1"
  role_name: "SageMakerExecutionRole"

# Cost Optimization
cost_optimization:
  cost_alert_threshold: 15  # USD per month
```

## Usage Examples

### Python Client
```python
from sagemaker_client import SageMakerClient

# Initialize client
client = SageMakerClient.from_env()

# Predict emotion from file
result = client.predict_emotion_from_file("audio.wav")
print(f"Emotion: {result.predicted_emotion}")
print(f"Confidence: {result.confidence}")
```

### Direct API Call
```python
import boto3
import json
import base64

client = boto3.client('sagemaker-runtime')

# Read and encode audio
with open("audio.wav", "rb") as f:
    audio_data = f.read()
audio_base64 = base64.b64encode(audio_data).decode('utf-8')

# Invoke endpoint
response = client.invoke_endpoint(
    EndpointName="your-endpoint-name",
    ContentType='application/json',
    Body=json.dumps({
        "audio_base64": audio_base64,
        "sample_rate": 16000
    })
)

result = json.loads(response['Body'].read())
print(result)
```

## Monitoring

### Health Check
```bash
poetry run python sagemaker_client.py --endpoint <ENDPOINT_NAME> --health
```

### Performance Monitoring
```bash
poetry run python ../scripts/monitor.py <ENDPOINT_NAME> --metrics
```

### Cost Monitoring
```bash
poetry run python ../scripts/monitor.py <ENDPOINT_NAME> --costs
```

## Cleanup

### Delete Endpoint
```bash
poetry run python deploy_model.py --delete <ENDPOINT_NAME>
```

### Full Cleanup
```bash
poetry run python ../scripts/cleanup.py --cleanup --days 30 --force
```

## Development

### Local Testing
```bash
# Test inference script locally
poetry run python inference.py --test

# Test with specific audio file
poetry run python inference.py --test --audio test_audio.wav
```

### Running Tests
```bash
# Run full test suite
poetry run python test_endpoint.py <ENDPOINT_NAME> --full

# Performance benchmark
poetry run python test_endpoint.py <ENDPOINT_NAME> --benchmark 50

# Test specific emotion
poetry run python test_endpoint.py <ENDPOINT_NAME> --emotion happy
```

## Cost Management

### Expected Monthly Costs
- **Serverless endpoint**: ~$0.000006208 per GB-second
- **Invocations**: ~$0.0000002 per request
- **Typical usage**: <$10/month for light experimentation

### Cost Optimization Tips
1. Use serverless endpoints for low traffic scenarios
2. Monitor usage with built-in monitoring tools
3. Set up cost alerts in CloudWatch
4. Delete unused endpoints promptly
5. Use appropriate memory limits (2GB sufficient for this model)

## Troubleshooting

Common issues and solutions can be found in the [troubleshooting guide](../docs/troubleshooting.md).

### Quick Checks
```bash
# Check AWS credentials
aws sts get-caller-identity

# List existing endpoints
poetry run python deploy_model.py --list

# Check endpoint status
poetry run python ../scripts/monitor.py <ENDPOINT_NAME> --health
```

## Support

For additional support:
1. Review the [deployment guide](../docs/deployment-guide.md)
2. Check the [API usage documentation](../docs/api-usage.md)
3. Refer to the [troubleshooting guide](../docs/troubleshooting.md)
4. Monitor CloudWatch logs for detailed error information

## Model Details

### Architecture
- **Base Model**: wav2vec2-large-xlsr-53
- **Fine-tuned for**: Speech emotion classification
- **Parameters**: 0.3B
- **Training Dataset**: RAVDESS
- **Accuracy**: 82.23%

### Input Requirements
- **Sample Rate**: 16kHz (recommended)
- **Channels**: Mono
- **Duration**: 1-30 seconds
- **Formats**: WAV, MP3, FLAC

### Output Format
```json
{
    "predicted_emotion": "happy",
    "confidence": 0.892,
    "all_emotions": {...},
    "top_3_emotions": [...],
    "model_info": {...}
}
```