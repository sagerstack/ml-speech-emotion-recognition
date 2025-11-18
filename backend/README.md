# ML Speech Emotion Recognition API

A production-ready FastAPI backend for speech emotion recognition with AWS SageMaker integration.

## 🚀 Features

- **FastAPI Framework**: Modern, fast Python web framework
- **AWS SageMaker Integration**: Deployed ML model inference
- **Authentication**: JWT Bearer Token authentication
- **Structured Logging**: JSON-formatted logs with correlation tracking
- **Code Quality**: Comprehensive linting, formatting, and type checking
- **Security**: Bandit security scanning
- **Testing**: pytest with asyncio support and coverage
- **Monitoring**: Prometheus metrics integration

## 📋 Requirements

- Python 3.11+
- Poetry (for dependency management)
- AWS Account (for SageMaker deployment)

## 🛠️ Development Setup

### 1. Install Dependencies

```bash
# Clone the repository
git clone <repository-url>
cd ml-speech-emotion-recognition/backend

# Install dependencies using Poetry
poetry install --with dev

# Activate the virtual environment
poetry shell
```

### 2. Environment Configuration

Create a `.env` file in the backend directory:

```env
# Application Configuration
DEBUG=true
HOST=0.0.0.0
PORT=8000

# AWS Configuration (us-east-1)
AWS_REGION=us-east-1
SAGEMAKER_ENDPOINT_NAME=test-emotion-endpoint

# Security Configuration
SECRET_KEY=your-secret-key-here

# Audio Processing
MAX_UPLOAD_SIZE_MB=30
MAX_AUDIO_DURATION_SECONDS=30

# Performance
MAX_CONCURRENT_REQUESTS=50
REQUEST_TIMEOUT_SECONDS=60

# Monitoring
PROMETHEUS_ENABLED=true
METRICS_PORT=9090
```

### 3. Run Development Server

```bash
# Using Poetry
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Using Makefile
make run
```

The API will be available at:
- **API**: http://localhost:8000
- **Documentation**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔧 Code Quality

### Available Commands

The project includes a Makefile with convenient commands:

```bash
# Install all dependencies
make install

# Run linter and fix issues
make lint

# Format code
make format

# Run type checking
make type-check

# Run security scan
make security

# Run all code quality checks
make check

# Run tests
make test

# Clean up caches
make clean
```

### Code Quality Tools

1. **Ruff**: Fast Python linter and formatter
   - Linting: `poetry run ruff check --fix`
   - Formatting: `poetry run ruff format`

2. **MyPy**: Static type checking
   - Command: `poetry run mypy app/ --ignore-missing-imports`

3. **Black**: Code formatting (fallback)
   - Command: `poetry run black app/`

4. **Bandit**: Security vulnerability scanning
   - Command: `poetry run bandit -r app/ -c pyproject.toml`

5. **pytest**: Unit testing with coverage
   - Command: `poetry run pytest --cov=app --cov-report=html`

### Pre-commit Hooks

Set up pre-commit hooks for automatic code quality checks:

```bash
make setup-hooks
```

Hooks configured:
- Ruff linting and formatting
- MyPy type checking
- Black formatting
- Bandit security scanning
- General code quality checks

## 🧪 Testing

### Run Tests

```bash
# Run all tests
make test

# Run tests with coverage
poetry run pytest --cov=app --cov-report=html --cov-report=term-missing

# Run specific test file
poetry run pytest tests/test_main.py
```

### Test Coverage

Coverage reports are generated in:
- Terminal output
- HTML report: `htmlcov/index.html`

## 📊 Monitoring

### Prometheus Metrics

The application exposes Prometheus metrics at:
- **Metrics**: http://localhost:9090/metrics

### Structured Logging

Logs are structured using `structlog` with:
- JSON format for production
- Pretty console format for development
- Correlation ID tracking

## 🔐 Security

### Authentication

- JWT Bearer Token authentication
- Configurable token expiration
- Secure token generation

### Security Scanning

- **Bandit**: Automated security vulnerability scanning
- **Configured exclusions**: Development-specific allowances
- **Regular scanning**: Integrated into CI/CD pipeline

## 🏗️ Architecture

### Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   └── utils/
│       ├── __init__.py
│       ├── config.py        # Configuration management
│       └── logging.py       # Structured logging setup
├── tests/                   # Test suite
├── .pre-commit-config.yaml  # Pre-commit hooks configuration
├── pyproject.toml          # Poetry configuration and dependencies
├── Makefile                # Development commands
└── README.md               # This file
```

### Configuration

- **Pydantic Settings**: Environment-based configuration
- **Type-safe**: Full type annotation support
- **Environment variables**: `.env` file support
- **Validation**: Automatic configuration validation

## 🚀 Deployment

### Development

```bash
# Development server with hot reload
make run
```

### Production

```bash
# Production server
make run-prod
```

### Docker

```bash
# Build image
docker build -t ml-emotion-api .

# Run container
docker run -p 8000:8000 ml-emotion-api
```

## 📚 API Documentation

### Endpoints

- `GET /`: Root endpoint
- `GET /health`: Health check
- `GET /docs`: Swagger UI documentation
- `GET /redoc`: ReDoc documentation
- `POST /v1/predict`: Emotion prediction endpoint

### Usage Examples

See the API documentation at http://localhost:8000/docs for detailed usage examples.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run code quality checks: `make check`
5. Run tests: `make test`
6. Submit a pull request

### Code Style

- Follow PEP 8 style guidelines
- Use type hints for all functions
- Add docstrings for all public functions
- Maintain 100% test coverage where possible

## 📝 License

This project is part of the ML Speech Emotion Recognition system.

## 🆘 Support

For issues and questions:
1. Check the [API Documentation](http://localhost:8000/docs)
2. Review the test files for usage examples
3. Check the configuration examples in this README