# HuggingFace Model Deployment to SageMaker Serverless Endpoint

## Overview

This document outlines the deployment plan for a cost-effective HuggingFace speech emotion recognition model to AWS SageMaker serverless endpoint for experimentation purposes.

## Selected Model

### Model Details
- **Model Name**: `ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition`
- **Model Size**: 0.3B parameters
- **Architecture**: wav2vec2-large-xlsr-53 fine-tuned for speech emotion classification
- **Accuracy**: 82.23% on RAVDESS dataset
- **License**: Apache 2.0 (commercial-friendly)
- **Emotion Classes**: 8 emotions from RAVDESS dataset

### Cost-Effectiveness Benefits
- Lightweight model requires minimal SageMaker serverless resources
- Low memory footprint (2GB sufficient)
- Fast inference times for cost optimization
- Pay-per-invocation pricing model
- No infrastructure management overhead

## SageMaker Serverless Configuration

### Endpoint Settings
- **Memory Size**: 2048 MB (2GB)
- **Max Concurrency**: 2 instances
- **Timeout**: 60 seconds
- **Region**: us-east-1 (consistent with project configuration)

### Estimated Cost Structure
- **Pricing**: Pay-per-invocation + memory provisioned
- **Cost Factors**:
  - Memory provisioned (2GB)
  - Request count
  - Invocation duration
  - Data transfer
- **Expected Monthly Cost**: <$10 for light experimentation workloads

## Implementation Tasks

### Phase 1: Preparation and Setup

#### Task 1: Environment Setup
- [ ] Create deployment/ directory structure
- [ ] Install required dependencies: `sagemaker`, `transformers`, `boto3`
- [ ] Configure AWS credentials and permissions
- [ ] Set up SageMaker execution role with necessary policies:
  - SageMaker access
  - S3 access for model artifacts
  - CloudWatch Logs access

#### Task 2: Model Analysis and Validation
- [ ] Download and test model locally
- [ ] Validate model input/output format
- [ ] Test with sample audio files
- [ ] Document preprocessing requirements:
  - Audio format (16kHz, mono)
  - Input tensor dimensions
  - Expected output format

### Phase 2: Model Deployment

#### Task 3: Model Packaging
- [ ] Create HuggingFace model script (`inference.py`)
- [ ] Define model loading and prediction functions
- [ ] Implement audio preprocessing pipeline
- [ ] Add error handling and input validation
- [ ] Create requirements.txt for model dependencies

#### Task 4: SageMaker Deployment Script
- [ ] Create `deploy_model.py` script
- [ ] Configure HuggingFace estimator for SageMaker
- [ ] Set up model artifact upload to S3
- [ ] Configure serverless endpoint configuration
- [ ] Implement deployment with retry logic

#### Task 5: Serverless Endpoint Creation
- [ ] Deploy model to SageMaker serverless endpoint
- [ ] Configure endpoint with specified parameters:
  - MemorySize: 2048
  - MaxConcurrency: 2
  - Timeout: 60
- [ ] Enable CloudWatch logging
- [ ] Set up endpoint monitoring

### Phase 3: Testing and Integration

#### Task 6: Endpoint Testing
- [ ] Create test script with sample audio files
- [ ] Test inference with various audio formats
- [ ] Validate response times under 60 seconds
- [ ] Test concurrent requests (max 2)
- [ ] Monitor CloudWatch metrics for performance

#### Task 7: Backend Integration
- [ ] Update backend ModelService with SageMaker client
- [ ] Implement invoke_endpoint functionality
- [ ] Add endpoint health checking
- [ ] Implement retry logic for failed requests
- [ ] Add monitoring and metrics collection

#### Task 8: Error Handling and Monitoring
- [ ] Implement comprehensive error handling:
  - Throttling exceptions
  - Model invocation errors
  - Network timeouts
  - Invalid input responses
- [ ] Set up CloudWatch alerts for:
  - High error rates
  - Long invocation times
  - Throttling events
- [ ] Create endpoint health dashboard

### Phase 4: Documentation and Cleanup

#### Task 9: Documentation
- [ ] Create deployment guide document
- [ ] Document API usage examples
- [ ] Create troubleshooting guide
- [ ] Document cost optimization strategies
- [ ] Update project architecture documentation

#### Task 10: Cleanup and Cost Management
- [ ] Implement automated cleanup scripts
- [ ] Set up cost monitoring alerts
- [ ] Create endpoint deletion procedures
- [ ] Document model versioning strategy

## File Structure

```
sagemaker/
├── model-deployment/
│   ├── deploy_model.py              # Main deployment script
│   ├── inference.py                 # Model inference script
│   ├── requirements.txt             # Model dependencies
│   ├── test_endpoint.py             # Endpoint testing script
│   ├── config.yaml                  # Deployment configuration
│   └── README.md                    # Deployment documentation
├── scripts/
│   ├── cleanup.py                   # Resource cleanup script
│   └── monitor.py                   # Cost monitoring script
└── docs/
    ├── deployment-guide.md          # Step-by-step deployment guide
    ├── api-usage.md                 # API documentation
    └── troubleshooting.md           # Common issues and solutions
```

## Risk Mitigation

### Technical Risks
1. **Model Size Underestimation**: Monitor memory usage, upgrade to 4GB if needed
2. **Timeout Issues**: Optimize inference code, monitor processing times
3. **Concurrency Limits**: Start with 2 instances, scale based on usage patterns
4. **Input Format Issues**: Comprehensive testing with various audio formats

### Cost Risks
1. **Unexpected High Usage**: Set up CloudWatch billing alerts
2. **Long-running Invocations**: Monitor and optimize inference times
3. **Data Transfer Costs**: Minimize payload sizes where possible

## Success Criteria

### Functional Requirements
- [ ] Model successfully deployed to SageMaker serverless endpoint
- [ ] Endpoint responds to emotion recognition requests
- [ ] Response times under 60 seconds
- [ ] Backend integration working seamlessly
- [ ] Error handling covers all failure scenarios

### Non-Functional Requirements
- [ ] Monthly costs under $10 for experimentation
- [ ] Endpoint availability > 99%
- [ ] Proper monitoring and alerting in place
- [ ] Documentation complete and usable
- [ ] Cleanup procedures tested and working

## Next Steps

After completing this deployment:
1. Test with real CREMA-D dataset audio files
2. Evaluate performance against your specific use cases
3. Consider upgrading to larger model (Whisper) if accuracy insufficient
4. Implement model versioning for production use
5. Set up CI/CD pipeline for automated deployments

## References

- [AWS SageMaker Serverless Documentation](https://docs.aws.amazon.com/sagemaker/latest/dg/serverless-endpoints.html)
- [HuggingFace SageMaker Integration](https://huggingface.co/docs/sagemaker/index)
- [Model Page](https://huggingface.co/ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition)
- [Example Deployment](https://github.com/aws/amazon-sagemaker-examples/blob/main/deploy_and_monitor/sm-host_pretrained_model_bert/sm-host_pretrained_model_bert.ipynb)