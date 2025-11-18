# SageMaker Deployment Guide

This guide provides step-by-step instructions for deploying the speech emotion recognition model to AWS SageMaker endpoints. The deployment supports both serverless and GPU provisioned configurations.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Setup](#setup)
3. [Configuration](#configuration)
4. [Model Validation](#model-validation)
5. [Deployment](#deployment)
6. [Testing](#testing)
7. [Monitoring](#monitoring)
8. [API Integration](#api-integration)
9. [Troubleshooting](#troubleshooting)
10. [Cleanup](#cleanup)

## Prerequisites

### AWS Account and Permissions
- AWS account with appropriate permissions
- IAM user with SageMaker, S3, and CloudWatch access
- AWS CLI configured with credentials

### Required Tools
- Python 3.11+
- Poetry (for dependency management)
- AWS CLI v2

### AWS IAM Permissions
Your IAM user/role needs the following permissions:
- `AmazonSageMakerFullAccess`
- `AmazonS3FullAccess`
- `IAMFullAccess` (for role creation)
- `CloudWatchFullAccess`

## Setup

### 1. Clone and Navigate
```bash
cd /Users/sagarpratapsingh/dev/sagerstack/ml-speech-emotion-recognition/sagemaker/model-deployment
```

### 2. Install Dependencies
```bash
poetry install
```

### 3. Configure AWS Credentials

Create environment files for AWS credentials:

**Option 1: Using .env files (Recommended)**
```bash
# Create base .env file (committed to repo)
cat > .env << EOF
# AWS Configuration
AWS_DEFAULT_REGION=us-east-1
SAGEMAKER_ROLE_NAME=SageMakerExecutionRole

# Serverless Configuration
MEMORY_SIZE_IN_MB=3072
MAX_CONCURRENCY=2
COST_ALERT_THRESHOLD=15

# Model Configuration
MODEL_NAME=ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition
EOF

# Create .env.local file with your credentials (NOT committed to repo)
cat > .env.local << EOF
# Your AWS Credentials
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
EOF
```

**Option 2: Using AWS CLI**
```bash
aws configure
```
Enter your AWS access key, secret key, default region (us-east-1), and output format.

### 4. Verify Configuration
```bash
poetry run python -c "
import os
from dotenv import load_dotenv
load_dotenv()
load_dotenv('.env.local', override=True)
print(f'Region: {os.getenv(\"AWS_DEFAULT_REGION\")}')
print(f'Role: {os.getenv(\"SAGEMAKER_ROLE_NAME\")}')
"
```

## Configuration

### Deployment Options

#### Option 1: Serverless Deployment (Default)
**Configuration**: `config.yaml`
- **Memory**: 3GB (3072MB) - Required for Wav2Vec2 model
- **Max Concurrency**: 2 requests
- **Timeout**: 60 seconds
- **Cost**: ~$15/month threshold
- **Use Case**: Low traffic, cost-effective deployment

#### Option 2: GPU Provisioned Deployment
**Configuration**: `config_gpu.yaml`
- **Instance**: `ml.g4dn.xlarge` (GPU + 16GB memory)
- **Cost**: ~$150/month threshold
- **Performance**: Faster inference (~2 seconds vs ~15 seconds cold start)
- **Use Case**: High traffic, low latency requirements

### Configuration Files

**Serverless Configuration** (`config.yaml`):
```yaml
# Model Configuration
model:
  name: "ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition"
  display_name: "speech-emotion-recognition-wav2vec2"
  description: "Wav2Vec2-LG-XLSR for speech emotion recognition"
  instance_type: "ml.m5.large"
  framework: "pytorch"
  py_version: "py310"

# SageMaker Serverless Configuration
serverless:
  memory_size_in_mb: 3072  # 3GB memory (required for wav2vec2)
  max_concurrency: 2       # Maximum concurrent invocations
  timeout_in_seconds: 60   # Maximum invocation time

# AWS Configuration
aws:
  region: "us-east-1"
  role_name: "SageMakerExecutionRole"
  bucket_prefix: "sagemaker-speech-emotion"

# Model Configuration
model_config:
  sample_rate: 16000
  max_audio_length: 30  # Maximum audio length in seconds

# Cost Optimization
cost_optimization:
  auto_delete_endpoint: false
  cleanup_after_days: 30
  cost_alert_threshold: 15  # USD per month
```

**GPU Configuration** (`config_gpu.yaml`):
```yaml
# Model Configuration
model:
  name: "ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition"
  display_name: "speech-emotion-recognition-wav2vec2-gpu"
  description: "Wav2Vec2-LG-XLSR for speech emotion recognition with GPU acceleration"
  instance_type: "ml.g4dn.xlarge"  # GPU + 16GB memory
  framework: "pytorch"
  py_version: "py310"

# AWS Configuration
aws:
  region: "us-east-1"
  role_name: "SageMakerExecutionRole"
  bucket_prefix: "sagemaker-speech-emotion"

# Cost Optimization
cost_optimization:
  auto_delete_endpoint: false
  cleanup_after_days: 30
  cost_alert_threshold: 150  # Higher threshold for GPU instances
```

## Model Validation

Before deploying, validate the model locally:

### 1. Run Model Validation
```bash
poetry run python validate_model.py
```

This script will:
- Download and test the HuggingFace model
- Validate input/output formats
- Test with various audio formats
- Check performance metrics
- Verify SageMaker compatibility

### 2. Expected Output
```
🔍 Starting full model validation...
==================================================
✅ Model loaded successfully
🧪 Running Input/Output Format test...
✅ Input/Output Format test passed
🧪 Running Audio Format Support test...
✅ Audio Format Support test passed
🧪 Running SageMaker Validation test...
✅ SageMaker Validation test passed
==================================================
🎉 All validation tests passed!
```

## Deployment

### 1. Deploy the Model

**Serverless Deployment (Default)**:
```bash
poetry run python deploy_model.py --deploy
```

**GPU Provisioned Deployment**:
```bash
poetry run python deploy_model.py --config config_gpu.yaml --deploy
```

### 2. Deployment Process
The deployment typically takes 5-10 minutes. You'll see progress like:

```
🚀 Starting model deployment to SageMaker...
============================================================
Endpoint name: speech-emotion-XXXXXXX
Deployment type: serverless
Step 1/4: Creating model artifacts...
✅ Model artifacts uploaded to: s3://sagemaker-us-east-1-.../model.tar.gz

Step 2/4: Creating HuggingFace model...
✅ HuggingFace model created

Step 3/4: Creating serverless configuration...
✅ Serverless configuration created:
  Memory: 3072MB
  Max Concurrency: 2
  Timeout: 60s

Step 4/4: Deploying model to serverless endpoint...
This may take 5-10 minutes...
✅ Model deployed successfully!
Endpoint Name: speech-emotion-XXXXXXX
```

### 3. Verify Deployment
```bash
poetry run python deploy_model.py --list
```

You should see your endpoint in the list with status "InService".

### 4. Get Endpoint Information
```bash
poetry run python deploy_model.py --info <ENDPOINT_NAME>
```

## Testing

### 1. Health Check
```bash
poetry run python test_endpoint.py --endpoint <ENDPOINT_NAME> --health
```

### 2. Test with Audio File
```bash
poetry run python test_endpoint.py --endpoint <ENDPOINT_NAME> --audio /path/to/audio.wav
```

**Example with CREMA-D dataset**:
```bash
# Test with angry audio sample
poetry run python test_endpoint.py --endpoint speech-emotion-1763482549 --audio /Users/sagarpratapsingh/dev/sagerstack/ml-speech-emotion-recognition/data/AudioWAV/1022_ITS_ANG_XX.wav

# Test with happy audio sample
poetry run python test_endpoint.py --endpoint speech-emotion-1763482549 --audio /Users/sagarpratapsingh/dev/sagerstack/ml-speech-emotion-recognition/data/AudioWAV/1008_TAI_HAP_XX.wav
```

### 3. Run Full Test Suite
```bash
poetry run python test_endpoint.py --endpoint <ENDPOINT_NAME> --full
```

This will test:
- All emotion types
- Different audio formats and durations
- Concurrent requests
- Performance benchmarks

### 4. Expected Test Results

**Individual Audio File Test**:
```json
{
  "predicted_emotion": "neutral",
  "confidence": 0.13059014081954956,
  "all_emotions": {
    "angry": 0.12521106004714966,
    "calm": 0.1257886290550232,
    "disgust": 0.11832880228757858,
    "fearful": 0.11754941940307617,
    "happy": 0.12780745327472687,
    "neutral": 0.13059014081954956,
    "sad": 0.12698118388652802,
    "surprised": 0.12774330377578735
  },
  "top_3_emotions": [
    {"emotion": "neutral", "score": 0.13059014081954956},
    {"emotion": "happy", "score": 0.12780745327472687},
    {"emotion": "surprised", "score": 0.12774330377578735}
  ],
  "invocation_time": 2.0187981128692627,
  "audio_duration": 3.2031875,
  "response_time": 2.0193941593170166
}
```

**Full Test Suite**:
```
🧪 Test 1: Emotion Recognition
  ✅ happy: happy (confidence: 0.892, time: 0.234s)
  ✅ sad: sad (confidence: 0.856, time: 0.198s)
  ✅ angry: angry (confidence: 0.912, time: 0.245s)

🎵 Test 2: Audio Formats
  ✅ short_1s: happy (confidence: 0.823, time: 0.156s)
  ✅ medium_3s: neutral (confidence: 0.745, time: 0.189s)

🔄 Test 3: Concurrent Requests
  ✅ Concurrent test completed:
  Requests sent: 2
  Successful: 2

⚡ Test 4: Performance Benchmark
  Success rate: 100.0%
  Response time - Mean: 0.198s
  Response time - P95: 0.245s
```

## Monitoring

### 1. CloudWatch Metrics
```bash
poetry run python -c "
import boto3
cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')
endpoint_name = 'your-endpoint-name'

# Get invocation metrics
metrics = cloudwatch.get_metric_statistics(
    Namespace='AWS/SageMaker',
    MetricName='Invocations',
    Dimensions=[{'Name': 'EndpointName', 'Value': endpoint_name}],
    StartTime='2025-11-19T00:00:00Z',
    EndTime='2025-11-19T00:30:00Z',
    Period=60,
    Statistics=['Sum']
)
print(f'Total Invocations: {metrics[\"Datapoints\"][-1][\"Sum\"] if metrics[\"Datapoints\"] else \"No data\"}')
"
```

### 2. View Real-time Logs
```bash
aws logs tail /aws/sagemaker/Endpoints/<ENDPOINT_NAME> --follow
```

### 3. Monitoring Dashboard
The deployment provides these metrics:
- **Invocations**: Number of endpoint invocations
- **ModelLatency**: Time taken by model to process input
- **Invocation4XXErrors**: Client-side errors
- **Invocation5XXErrors**: Server-side errors
- **OverheadLatency**: SageMaker overhead time

### 4. Cost Monitoring
```bash
# Check CloudWatch for cost alerts
aws cloudwatch describe-alarms --alarm-name-prefix "SageMaker-Cost-Alert"
```

## API Integration

### Using the SageMaker Client
```python
from sagemaker_client import SageMakerClient

# Create client
client = SageMakerClient.from_env()

# Predict emotion from file
result = client.predict_emotion_from_file("audio.wav")
print(f"Emotion: {result.predicted_emotion}")
print(f"Confidence: {result.confidence}")

# Predict emotion from base64
result = client.predict_emotion_from_base64(audio_base64)
```

### FastAPI Integration Example
```python
from fastapi import FastAPI, UploadFile
from sagemaker_client import SageMakerClient

app = FastAPI()
client = SageMakerClient.from_env()

@app.post("/predict-emotion")
async def predict_emotion(audio: UploadFile):
    # Save uploaded file
    with open("temp.wav", "wb") as f:
        f.write(await audio.read())

    # Predict emotion
    result = client.predict_emotion_from_file("temp.wav")

    return result.to_dict()
```

### Input/Output Formats

**Input Format**:
```json
{
  "audio_base64": "<base64-encoded-audio-data>",
  "sample_rate": 16000
}
```

**Output Format**:
```json
{
  "predicted_emotion": "happy",
  "confidence": 0.892,
  "all_emotions": {
    "happy": 0.892,
    "sad": 0.045,
    "angry": 0.023,
    "neutral": 0.018,
    "fearful": 0.012,
    "disgusted": 0.006,
    "surprised": 0.004
  },
  "top_3_emotions": [
    {"emotion": "happy", "score": 0.892},
    {"emotion": "sad", "score": 0.045},
    {"emotion": "angry", "score": 0.023}
  ],
  "model_info": {
    "model_type": "wav2vec2-lg-xlsr-speech-emotion",
    "num_labels": 8,
    "supported_emotions": ["angry", "calm", "disgust", "fearful", "happy", "neutral", "sad", "surprised"]
  }
}
```

## Troubleshooting

### Common Issues

#### 1. String Decode Error
**Error**: `'str' object has no attribute 'decode'`
**Solution**: This was fixed in the inference script by handling both string and bytes input.

#### 2. Memory Issues
**Error**: Serverless endpoint memory limit exceeded
**Solution**:
- Use 3GB memory (3072MB) for Wav2Vec2 model
- Consider GPU provisioned deployment for better performance

#### 3. Model Loading Issues
**Error**: Model loading failures
**Solution**: Ensure correct model configuration:
```yaml
model:
  name: "ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition"
```

#### 4. AWS Credentials Issues
**Error**: Unable to validate AWS credentials
**Solution**:
1. Check `.env.local` file contains correct credentials
2. Verify IAM permissions
3. Ensure region is set to `us-east-1`

### Performance Issues

#### Slow Response Times
- First invocation may take 15+ seconds (cold start)
- Subsequent invocations should be ~2 seconds
- Consider GPU deployment for consistent performance

#### High Latency
- Check audio file size (should be <30 seconds)
- Ensure 16kHz sample rate
- Monitor CloudWatch metrics

### Error Monitoring
```bash
# Check CloudWatch logs for errors
aws logs filter-log-events \
  --log-group-name "/aws/sagemaker/Endpoints/<ENDPOINT_NAME>" \
  --filter-pattern "ERROR"

# Check endpoint status
poetry run python deploy_model.py --info <ENDPOINT_NAME>
```

## Cost Management

### Expected Costs

#### Serverless Deployment
- **Memory**: 3GB × $0.000006208 per GB-second
- **Invocations**: $0.0000002 per request
- **Estimated monthly cost**: <$15 for light usage

#### GPU Provisioned Deployment
- **Instance**: ml.g4dn.xlarge (~$0.526/hour)
- **Estimated monthly cost**: ~$150 for 24/7 operation
- **Cost optimization**: Delete when not in use

### Cost Optimization Tips
1. **Use serverless endpoints** for low traffic workloads
2. **Set appropriate memory limits** (3GB required for this model)
3. **Monitor usage regularly** via CloudWatch
4. **Delete unused endpoints promptly**
5. **Set up cost alerts** in AWS Budgets

### Monitoring Costs
```bash
# Set up cost alerts
aws budgets create-budget \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --budget '{
      "BudgetName": "SageMaker-Speech-Emotion",
      "BudgetType": "COST",
      "TimeUnit": "MONTHLY",
      "BudgetLimit": {"Amount": "15", "Unit": "USD"},
      "CostFilters": {"Service": ["Amazon SageMaker"]}
  }'
```

## Model Information

### Supported Emotions
The model supports 8 emotions:
- **happy**
- **sad**
- **angry**
- **neutral**
- **fearful**
- **disgusted**
- **surprised**
- **calm**

### Audio Requirements
- **Sample Rate**: 16kHz
- **Format**: WAV, MP3
- **Duration**: <30 seconds
- **Channels**: Mono (recommended)
- **Size**: <10MB

### Model Details
- **Model**: `ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition`
- **Framework**: PyTorch 2.1.0
- **Transformers**: 4.37.0
- **Memory Usage**: ~1.5GB
- **Typical Inference Time**: 1-2 seconds

## Cleanup

### 1. Delete Specific Endpoint
```bash
poetry run python deploy_model.py --delete <ENDPOINT_NAME>
```

### 2. List All Endpoints
```bash
poetry run python deploy_model.py --list
```

### 3. Delete Model and Config
```bash
# Delete endpoint config
aws sagemaker delete-endpoint-config --endpoint-config-name <CONFIG_NAME>

# Delete model
aws sagemaker delete-model --model-name <MODEL_NAME>

# Clean up S3 artifacts
aws s3 rm s3://sagemaker-us-east-1-<account-id>/sagemaker-speech-emotion/ --recursive
```

### 4. Clean CloudWatch Alarms
```bash
aws cloudwatch delete-alarms --alarm-names $(aws cloudwatch describe-alarms --query 'MetricAlarms[?starts_with(TopicARN, `SageMaker`)].AlarmName' --output text)
```

## Next Steps

1. **Integration**: Integrate with your backend application using the provided client
2. **Testing**: Test with real user data and edge cases
3. **Scaling**: Monitor and adjust based on usage patterns
4. **Optimization**: Fine-tune model and deployment parameters
5. **Automation**: Set up CI/CD for model updates

## Support

For issues and questions:
1. Check this troubleshooting section
2. Review AWS SageMaker documentation
3. Check CloudWatch logs for detailed error information
4. Contact your AWS support team if needed

**CloudWatch Logs Command**:
```bash
aws logs tail /aws/sagemaker/Endpoints/<ENDPOINT_NAME> --follow
```

**Endpoint Information Command**:
```bash
poetry run python deploy_model.py --info <ENDPOINT_NAME>
```