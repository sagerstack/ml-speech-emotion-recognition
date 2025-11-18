# Makefile for ML Speech Emotion Recognition API
# Provides convenient commands for development and code quality

.PHONY: help install lint format type-check test clean run build check

# Default target
help:
	@echo "Available commands:"
	@echo "  install     Install dependencies"
	@echo "  lint        Run linter (ruff)"
	@echo "  format      Format code (ruff format)"
	@echo "  type-check  Run type checker (mypy)"
	@echo "  test        Run tests"
	@echo "  clean       Clean up caches and artifacts"
	@echo "  run         Run the development server"
	@echo "  build       Build for production"
	@echo "  check       Run all code quality checks"

# Install dependencies
install:
	poetry install --with dev

# Run linter and fix issues
lint:
	poetry run ruff check --fix

# Format code
format:
	poetry run ruff format

# Run type checking
type-check:
	poetry run mypy app/ --ignore-missing-imports

# Run tests
test:
	poetry run pytest

# Clean up
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	poetry cache clear pypi --all 2>/dev/null || true

# Run development server
run:
	poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run production server
run-prod:
	poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000

# Build for production
build:
	poetry build

# Run all code quality checks
check: lint format type-check
	@echo "✅ All code quality checks passed!"

# Install pre-commit hooks
setup-hooks:
	poetry run pre-commit install

# Run security check
security:
	poetry run bandit -r app/ -c pyproject.toml

# Update dependencies
update:
	poetry update

# Show dependency tree
deps:
	poetry show --tree