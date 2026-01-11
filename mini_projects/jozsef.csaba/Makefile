.PHONY: install install-dev install-test run test lint format clean help

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install production dependencies
	pip install -e .

install-dev:  ## Install development dependencies
	pip install -e ".[dev,test]"

install-test:  ## Install test dependencies only
	pip install -e ".[test]"

run:  ## Run the API server
	python app/main.py

dev:  ## Run the API server in development mode
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

demo:  ## Run the interactive demo
	python demo.py

test:  ## Run tests
	pytest

test-cov:  ## Run tests with coverage report
	pytest --cov=app --cov-report=html --cov-report=term-missing

test-verbose:  ## Run tests with verbose output
	pytest -v

lint:  ## Run linting
	ruff check app/ tests/

lint-fix:  ## Run linting and fix issues
	ruff check --fix app/ tests/

format:  ## Format code with black
	black app/ tests/

format-check:  ## Check code formatting
	black --check app/ tests/

clean:  ## Clean up generated files
	rm -rf __pycache__ .pytest_cache .coverage htmlcov
	rm -rf *.egg-info build dist
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.pyo' -delete

init-kb:  ## Initialize knowledge base
	python scripts/init_kb.py

rebuild-kb:  ## Rebuild knowledge base from scratch
	python scripts/init_kb.py --rebuild

docker-build:  ## Build Docker image
	docker build -t customer-service-triage-agent .

docker-run:  ## Run Docker container
	docker run -p 8000:8000 --env-file .env customer-service-triage-agent

all: install-dev init-kb  ## Install everything and initialize KB
