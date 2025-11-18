# Makefile for ML Speech Emotion Recognition React Dashboard
# Provides convenient commands for development and code quality

.PHONY: help install lint lint-fix format format-check type-check test test-watch build quality quality-fix clean run

# Default target
help:
	@echo "Available commands:"
	@echo "  install       Install dependencies"
	@echo "  lint          Run linter (ESLint)"
	@echo "  lint-fix      Auto-fix linting issues"
	@echo "  format        Format code (Prettier)"
	@echo "  format-check  Check code formatting"
	@echo "  type-check    Run TypeScript type checking"
	@echo "  test          Run tests"
	@echo "  test-watch    Run tests in watch mode"
	@echo "  build         Build for production"
	@echo "  quality       Run all code quality checks"
	@echo "  quality-fix   Auto-fix code quality issues"
	@echo "  clean         Clean up build artifacts"
	@echo "  run           Run development server"

# Install dependencies
install:
	npm install

# Run linter and check for issues
lint:
	npm run lint

# Auto-fix linting issues
lint-fix:
	npm run lint:fix

# Check code formatting
format-check:
	npm run format:check

# Format code
format:
	npm run format

# Run TypeScript type checking
type-check:
	npm run type-check

# Run tests
test:
	npm run test

# Run tests in watch mode
test-watch:
	npm run test -- --watch

# Build for production
build:
	npm run build

# Clean up build artifacts
clean:
	rm -rf build/
	rm -rf node_modules/.cache/

# Run development server
run:
	npm start

# Run all code quality checks
quality: lint format-check type-check
	@echo "✅ All code quality checks passed!"

# Auto-fix all code quality issues
quality-fix: lint-fix format
	@echo "✅ Code quality issues fixed!"

# Update dependencies
update:
	npm update

# Check for outdated dependencies
outdated:
	npm outdated

# Audit dependencies for security vulnerabilities
audit:
	npm audit
	npm audit fix