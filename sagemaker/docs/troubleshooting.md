# SageMaker Deployment Troubleshooting Guide

This guide provides solutions to common issues encountered during SageMaker deployment and usage of the speech emotion recognition endpoint.

## Table of Contents

1. [Deployment Issues](#deployment-issues)
2. [Endpoint Issues](#endpoint-issues)
3. [Performance Issues](#performance-issues)
4. [Authentication Issues](#authentication-issues)
5. [Cost Issues](#cost-issues)
6. [Audio Processing Issues](#audio-processing-issues)
7. [Monitoring Issues](#monitoring-issues)
8. [Debugging Tools](#debugging-tools)

## Deployment Issues

### Issue: Model Loading Timeout
**Error**: `Model timeout error: The model took longer than 60 seconds to load`

**Causes**:
- Model too large for specified memory
- Network issues downloading model from HuggingFace
- Insufficient permissions

**Solutions**:
```bash
# 1. Check model size
poetry run python model-deployment/validate_model.py

# 2. Increase memory size (edit config.yaml)
serverless:
  memory_size_in_mb: 4096  # Increase from 2048

# 3. Check network connectivity
curl -I https://huggingface.co

# 4. Verify IAM permissions
aws iam get-role-policy --role-name SageMakerExecutionRole --policy-name SageMakerExecutionRolePolicy
```

### Issue: IAM Role Creation Failed
**Error**: `Failed to create role: AccessDenied`

**Causes**:
- Insufficient IAM permissions
- Role already exists with different trust policy

**Solutions**:
```bash
# 1. Check existing roles
aws iam list-roles --query 'Roles[?contains(RoleName, `SageMaker`) == `true`]'

# 2. Use existing role
export SAGEMAKER_ROLE_ARN="arn:aws:iam::account:role/ExistingSageMakerRole"

# 3. Create role manually
aws iam create-role \
  --role-name SageMakerExecutionRole \
  --assume-role-policy-document file://trust-policy.json

aws iam attach-role-policy \
  --role-name SageMakerExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess
```

### Issue: S3 Upload Failed
**Error**: `Failed to upload model artifacts: S3 upload failed`

**Causes**:
- Incorrect S3 permissions
- Bucket doesn't exist
- Network connectivity issues

**Solutions**:
```bash
# 1. Check S3 permissions
aws s3 ls sagemaker-*

# 2. Create bucket manually
aws s3 mb s3://sagemaker-your-region-account-id

# 3. Test S3 access
aws s3 cp test.txt s3://your-bucket/test.txt

# 4. Check bucket policy
aws s3api get-bucket-policy --bucket your-bucket
```

### Issue: Endpoint Creation Failed
**Error**: `Failed to create endpoint: Validation error`

**Causes**:
- Invalid configuration
- Model compatibility issues
- Resource limits exceeded

**Solutions**:
```bash
# 1. Validate configuration
poetry run python -c "import yaml; yaml.safe_load(open('model-deployment/config.yaml'))"

# 2. Check model compatibility
poetry run python model-deployment/validate_model.py

# 3. Check service limits
aws service-quotas list-service-quotas --service-code sagemaker

# 4. Enable detailed logging
aws logs describe-log-groups --log-group-name-prefix /aws/sagemaker
```

## Endpoint Issues

### Issue: Endpoint Stuck in Creating
**Status**: `Creating` for > 30 minutes

**Causes**:
- Model loading issues
- Insufficient resources
- Configuration errors

**Solutions**:
```bash
# 1. Check CloudWatch logs
aws logs tail /aws/sagemaker/Endpoints/your-endpoint-name --follow

# 2. Describe endpoint status
aws sagemaker describe-endpoint --endpoint-name your-endpoint-name

# 3. Check for failures
aws sagemaker describe-endpoint --endpoint-name your-endpoint-name --query 'FailureReason'

# 4. Delete and redeploy
poetry run python model-deployment/deploy_model.py --delete your-endpoint-name
poetry run python model-deployment/deploy_model.py --deploy
```

### Issue: Endpoint Returns 4XX Errors
**Error**: `ModelError: Model failed to load`

**Causes**:
- Model artifacts corrupted
- Inference script errors
- Dependency issues

**Solutions**:
```bash
# 1. Check inference script locally
poetry run python model-deployment/inference.py --test

# 2. Verify model artifacts
aws s3 ls s3://your-bucket/path/to/model.tar.gz

# 3. Download and test artifacts
aws s3 cp s3://your-bucket/path/to/model.tar.gz .
tar -tzf model.tar.gz

# 4. Check model logs
aws logs filter-log-events \
  --log-group-name /aws/sagemaker/Endpoints/your-endpoint-name \
  --filter-pattern "ERROR"
```

### Issue: Endpoint Not Responding
**Error**: `ServiceUnavailable: The endpoint is currently unavailable`

**Causes**:
- Endpoint scaling issues
- Model crashes
- Infrastructure problems

**Solutions**:
```bash
# 1. Check endpoint status
poetry run python ../scripts/monitor.py your-endpoint-name --health

# 2. Check recent metrics
poetry run python ../scripts/monitor.py your-endpoint-name --metrics

# 3. Restart endpoint
aws sagemaker update-endpoint-weights-and-capacities \
  --endpoint-name your-endpoint-name \
  --desired-weights-and-capacities DesiredWeight=1,DesiredInstanceCount=1

# 4. Check service health
aws health get-event-accounts --filter=eventStatusCodes=open,upcoming
```

## Performance Issues

### Issue: High Latency
**Symptom**: Response times > 10 seconds

**Causes**:
- Cold start issues
- Large audio files
- Model optimization

**Solutions**:
```bash
# 1. Warm up endpoint
poetry run python model-deployment/test_endpoint.py your-endpoint-name --emotion happy

# 2. Optimize audio input
# - Use 16kHz sample rate
# - Limit to 30 seconds
# - Use mono channel

# 3. Check performance metrics
poetry run python model-deployment/test_endpoint.py your-endpoint-name --benchmark 10

# 4. Increase memory if needed
# Edit config.yaml to increase memory_size_in_mb
```

### Issue: Memory Constraints
**Error**: `ModelError: The model could not be loaded due to memory constraints`

**Causes**:
- Model too large for memory
- Multiple concurrent requests
- Memory leaks

**Solutions**:
```bash
# 1. Increase memory allocation
serverless:
  memory_size_in_mb: 4096  # or 6144

# 2. Reduce concurrency
serverless:
  max_concurrency: 1

# 3. Monitor memory usage
poetry run python ../scripts/monitor.py your-endpoint-name --metrics

# 4. Check CloudWatch memory metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/SageMaker \
  --metric-name MemoryUtilization \
  --dimensions Name=EndpointName,Value=your-endpoint-name \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Average
```

### Issue: Throttling
**Error**: `ThrottlingException: Rate exceeded`

**Causes**:
- Too many concurrent requests
- API rate limits
- Service limits

**Solutions**:
```bash
# 1. Implement exponential backoff
# See API usage guide for Python implementation

# 2. Reduce request rate
# Limit to max_concurrency (default 2)

# 3. Batch requests
poetry run python sagemaker_client.py batch-process

# 4. Request limit increase
aws support create-case \
  --service-code amazon-sagemaker \
  --category "Service Limits" \
  --subject "Request limit increase for serverless endpoints"
```

## Authentication Issues

### Issue: Access Denied
**Error**: `AccessDenied: User is not authorized to perform: sagemaker:InvokeEndpoint`

**Causes**:
- Insufficient IAM permissions
- Incorrect credentials
- Role trust issues

**Solutions**:
```bash
# 1. Verify current credentials
aws sts get-caller-identity

# 2. Check IAM policies
aws iam list-attached-user-policies --user-name $(aws sts get-caller-identity --query User.UserName --output text)

# 3. Add required policy
aws iam attach-user-policy \
  --user-name your-username \
  --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess

# 4. Test permissions
aws sagemaker list-endpoints
```

### Issue: Invalid Signature
**Error**: `SignatureDoesNotMatch: The request signature we calculated does not match`

**Causes**:
- Incorrect AWS region
- System time sync issues
- Credential formatting

**Solutions**:
```bash
# 1. Check region settings
aws configure get region

# 2. Sync system time
sudo ntpdate -s time.nist.gov

# 3. Verify credentials format
aws configure list

# 4. Refresh credentials
aws configure
```

### Issue: Temporary Credentials Expired
**Error**: `ExpiredTokenException: The security token included in the request is expired`

**Causes**:
- Temporary credentials expired
- Session token invalid

**Solutions**:
```bash
# 1. Refresh temporary credentials
aws sts get-session-token --duration-seconds 3600

# 2. Update environment variables
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=...

# 3. Use instance profiles (if on EC2)
aws configure set profile.ec2.role_arn arn:aws:iam::account:role/EC2SageMakerRole

# 4. Set up long-lived credentials for development
aws iam create-access-key --user-name your-username
```

## Cost Issues

### Issue: Unexpected High Costs
**Symptom**: Monthly charges exceed expected budget

**Causes**:
- High invocation volume
- Large memory allocation
- Unused endpoints running

**Solutions**:
```bash
# 1. Check cost breakdown
poetry run python ../scripts/monitor.py your-endpoint-name --costs

# 2. Monitor usage patterns
poetry run python ../scripts/monitor.py your-endpoint-name --monitor 60

# 3. Identify unused resources
poetry run python ../scripts/cleanup.py --identify --days 7

# 4. Set up cost alerts
aws cloudwatch put-metric-alarm \
  --alarm-name HighSageMakerCosts \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --threshold 10.0 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1
```

### Issue: Cost Optimization
**Goal**: Reduce monthly costs below $10

**Strategies**:
```bash
# 1. Reduce memory allocation
serverless:
  memory_size_in_mb: 2048  # Minimum for this model

# 2. Reduce concurrency
serverless:
  max_concurrency: 1

# 3. Implement auto-deletion
# Set up script to delete endpoint after period of inactivity

# 4. Use on-demand endpoints for testing
# Deploy to smaller instance for development

# 5. Monitor costs regularly
poetry run python ../scripts/monitor.py your-endpoint-name --costs
```

## Audio Processing Issues

### Issue: Unsupported Audio Format
**Error**: `Invalid input: Audio format not supported`

**Causes**:
- Unsupported file format
- Corrupted audio files
- Incorrect sample rate

**Solutions**:
```python
# 1. Validate audio format
import librosa
import soundfile as sf

def validate_audio(file_path):
    try:
        audio, sr = librosa.load(file_path, sr=None)
        print(f"Format: {sr}Hz, Duration: {len(audio)/sr:.2f}s")
        return True
    except Exception as e:
        print(f"Invalid audio: {e}")
        return False

# 2. Convert to supported format
def convert_audio(input_path, output_path, target_sr=16000):
    audio, sr = librosa.load(input_path, sr=target_sr)
    sf.write(output_path, audio, target_sr)

# 3. Check file integrity
def check_file_integrity(file_path):
    with open(file_path, 'rb') as f:
        header = f.read(44)  # WAV header
    return len(header) == 44 and header.startswith(b'RIFF')
```

### Issue: Poor Recognition Accuracy
**Symptom**: Model returns low confidence scores or incorrect emotions

**Causes**:
- Poor audio quality
- Background noise
- Non-speech audio
- Different language/accent

**Solutions**:
```python
# 1. Preprocess audio
import librosa
import numpy as np

def preprocess_audio(audio_path, output_path):
    # Load audio
    audio, sr = librosa.load(audio_path, sr=16000)

    # Remove silence
    audio, _ = librosa.effects.trim(audio, top_db=20)

    # Apply noise reduction
    audio = librosa.effects.preemphasis(audio)

    # Normalize
    audio = librosa.util.normalize(audio)

    # Save processed audio
    sf.write(output_path, audio, 16000)

# 2. Test with known good samples
poetry run python model-deployment/test_endpoint.py your-endpoint-name --emotion happy

# 3. Check confidence thresholds
if result.confidence < 0.5:
    print("Low confidence - consider re-recording")

# 4. Use ensemble approach (multiple predictions)
def ensemble_predict(audio_file, client, num_predictions=3):
    predictions = []
    for _ in range(num_predictions):
        result = client.predict_emotion_from_file(audio_file)
        predictions.append(result)

    # Average predictions
    avg_confidence = sum(p.confidence for p in predictions) / len(predictions)
    most_common = max(set(p.predicted_emotion for p in predictions),
                     key=lambda x: sum(1 for p in predictions if p.predicted_emotion == x))

    return most_common, avg_confidence
```

### Issue: Audio Length Problems
**Error**: `Invalid input: Audio too long/short`

**Causes**:
- Audio exceeds 30-second limit
- Audio too short (< 1 second)
- Empty audio files

**Solutions**:
```python
# 1. Check and trim audio length
def validate_and_trim_audio(audio_path, max_length=30, min_length=1):
    audio, sr = librosa.load(audio_path, sr=16000)
    duration = len(audio) / sr

    if duration > max_length:
        # Trim to max_length
        max_samples = max_length * sr
        audio = audio[:max_samples]
        print(f"Trimmed to {max_length} seconds")

    elif duration < min_length:
        raise ValueError(f"Audio too short: {duration:.2f}s (minimum: {min_length}s)")

    return audio, sr

# 2. Pad short audio with silence
def pad_audio(audio, sr, target_length=3):
    target_samples = target_length * sr
    current_samples = len(audio)

    if current_samples < target_samples:
        silence = np.zeros(target_samples - current_samples)
        audio = np.concatenate([audio, silence])

    return audio

# 3. Validate file before processing
def validate_file_before_upload(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    if os.path.getsize(file_path) == 0:
        raise ValueError("File is empty")

    try:
        duration = librosa.get_duration(filename=file_path)
        if duration < 0.5 or duration > 60:
            raise ValueError(f"Invalid duration: {duration:.2f}s")
    except Exception as e:
        raise ValueError(f"Invalid audio file: {e}")
```

## Monitoring Issues

### Issue: No Metrics Available
**Symptom**: CloudWatch metrics show no data

**Causes**:
- Endpoint not receiving traffic
- Metrics not configured
- Permissions issues

**Solutions**:
```bash
# 1. Test endpoint to generate metrics
poetry run python sagemaker_client.py --endpoint your-endpoint-name --health

# 2. Check CloudWatch permissions
aws logs describe-log-groups --log-group-name-prefix /aws/sagemaker

# 3. Verify metric namespace
aws cloudwatch list-metrics --namespace AWS/SageMaker

# 4. Force metric generation
for i in {1..5}; do
  poetry run python sagemaker_client.py --endpoint your-endpoint-name --health
  sleep 1
done
```

### Issue: Alarms Not Triggering
**Symptom**: CloudWatch alarms not firing when expected

**Causes**:
- Alarm configuration incorrect
- Insufficient data points
- Wrong thresholds

**Solutions**:
```bash
# 1. Check alarm configuration
aws cloudwatch describe-alarms --alarm-names your-alarm-name

# 2. Test alarm manually
aws cloudwatch set-alarm-state \
  --alarm-name your-alarm-name \
  --state-value ALARM \
  --state-reason "Manual test"

# 3. Verify metric data exists
aws cloudwatch get-metric-statistics \
  --namespace AWS/SageMaker \
  --metric-name Invocations \
  --dimensions Name=EndpointName,Value=your-endpoint-name \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Sum

# 4. Adjust alarm thresholds
aws cloudwatch put-metric-alarm \
  --alarm-name your-alarm-name \
  --metric-name Invocations \
  --namespace AWS/SageMaker \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

## Debugging Tools

### 1. Local Model Testing
```bash
# Test model locally before deployment
poetry run python model-deployment/validate_model.py

# Test inference script locally
poetry run python model-deployment/inference.py --test

# Create test audio files
poetry run python -c "
import numpy as np
import soundfile as sf
audio = np.random.randn(16000).astype(np.float32)
sf.write('test_audio.wav', audio, 16000)
"
```

### 2. Endpoint Diagnostics
```bash
# Comprehensive endpoint check
poetry run python ../scripts/monitor.py your-endpoint-name --report full_report.json

# Test all emotions
poetry run python model-deployment/test_endpoint.py your-endpoint-name --full

# Performance benchmark
poetry run python model-deployment/test_endpoint.py your-endpoint-name --benchmark 50
```

### 3. Log Analysis
```bash
# Tail CloudWatch logs
aws logs tail /aws/sagemaker/Endpoints/your-endpoint-name --follow

# Filter error logs
aws logs filter-log-events \
  --log-group-name /aws/sagemaker/Endpoints/your-endpoint-name \
  --filter-pattern "ERROR" \
  --start-time $(date -u -v-1H +%s)000

# Export logs for analysis
aws logs get-log-events \
  --log-group-name /aws/sagemaker/Endpoints/your-endpoint-name \
  --log-stream-name your-log-stream-name \
  --output text > endpoint_logs.txt
```

### 4. Network Diagnostics
```bash
# Test network connectivity
curl -I https://runtime.sagemaker.us-east-1.amazonaws.com

# Test AWS connectivity
aws sagemaker list-endpoints

# Check DNS resolution
nslookup runtime.sagemaker.us-east-1.amazonaws.com

# Test latency
ping -c 5 runtime.sagemaker.us-east-1.amazonaws.com
```

### 5. Resource Monitoring
```bash
# Check AWS service health
aws health get-events --filter=eventStatusCodes=open

# Monitor service quotas
aws service-quotas list-service-quotas --service-code sagemaker

# Check account limits
aws sagemaker describe-endpoint-config --endpoint-config-name your-endpoint-name

# Track resource usage over time
poetry run python ../scripts/monitor.py your-endpoint-name --monitor 1440  # Daily monitoring
```

## Getting Help

### 1. Collect Diagnostic Information
```bash
# Create diagnostic package
mkdir diagnostics
cd diagnostics

# Endpoint info
aws sagemaker describe-endpoint --endpoint-name your-endpoint-name > endpoint_info.json

# Recent metrics
poetry run python ../scripts/monitor.py your-endpoint-name --metrics > metrics.json

# Recent logs
aws logs filter-log-events \
  --log-group-name /aws/sagemaker/Endpoints/your-endpoint-name \
  --start-time $(date -u -v-6H +%s)000 > logs.json

# Configuration
cp ../model-deployment/config.yaml config.yaml

# Test results
poetry run python ../model-deployment/test_endpoint.py your-endpoint-name --emotion happy > test_result.json
```

### 2. Common Resources
- [AWS SageMaker Documentation](https://docs.aws.amazon.com/sagemaker/)
- [HuggingFace SageMaker Integration](https://huggingface.co/docs/sagemaker/index)
- [AWS Support Center](https://aws.amazon.com/support/)
- [AWS Developer Forums](https://forums.aws.amazon.com/)

### 3. Contact Information
- Internal support team
- AWS Support (for account-specific issues)
- HuggingFace community (for model-specific issues)

Remember to check the [deployment guide](deployment-guide.md) and [API usage guide](api-usage.md) for additional information and best practices.