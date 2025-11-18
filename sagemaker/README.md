# SageMaker Deployment Module

This module contains the deployment scripts and configurations for deploying the speech emotion recognition model to AWS SageMaker serverless endpoints.

## Project Structure

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

## Setup

1. Install dependencies using Poetry:
```bash
poetry install
```

2. Configure AWS credentials:
```bash
aws configure
```

3. Deploy the model:
```bash
poetry run python model-deployment/deploy_model.py
```

## Model Details

- **Model Name**: `ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition`
- **Memory Size**: 2GB
- **Max Concurrency**: 2
- **Timeout**: 60 seconds

## Cost Optimization

The serverless endpoint is configured for cost-effective experimentation:
- Pay-per-invocation pricing
- Minimal memory footprint (2GB)
- Low concurrency limits
- Expected monthly cost: <$10

## Documentation

See the `docs/` directory for detailed documentation:
- `deployment-guide.md`: Step-by-step deployment instructions
- `api-usage.md`: API usage examples
- `troubleshooting.md`: Common issues and solutions