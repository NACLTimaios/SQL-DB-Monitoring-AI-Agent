.PHONY: help setup-env secure-permissions init-db run test clean install-deps

help:
	@echo "SQL Agent Management Commands"
	@echo ""
	@echo "Setup and Installation:"
	@echo "  make install-deps          Install Python dependencies"
	@echo "  make setup-env              Set up environment variables from .env.example"
	@echo "  make secure-permissions     Set secure file permissions (600 for sensitive files)"
	@echo "  make init-db                Initialize the agent database"
	@echo ""
	@echo "Running:"
	@echo "  make run                   Start the API server"
	@echo ""
	@echo "Testing and Security:"
	@echo "  make test                  Run test suite"
	@echo "  make security-audit        Scan dependencies for known vulnerabilities"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean                 Remove __pycache__ and .pytest_cache"
	@echo ""

install-deps:
	@echo "Installing Python dependencies..."
	pip install -r requirements.txt

setup-env:
	@echo "Setting up environment variables..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✓ Created .env from .env.example"; \
		echo "⚠️  Please edit .env and set all required environment variables"; \
	else \
		echo "✓ .env already exists"; \
	fi
	@echo ""
	@echo "Required environment variables:"
	@echo "  SECRET_KEY                 JWT secret key (generate with: python3 -c \"import secrets; print(secrets.token_urlsafe(32))\")"
	@echo "  AGENT_DB_PASSWORD          Password for agent_store database"
	@echo "  MONITORED_DB_PASSWORD      Password for monitored database"
	@echo "  CORS_ORIGINS               Comma-separated list of allowed origins"
	@echo "  ALLOWED_HOSTS              Comma-separated list of allowed hosts"

secure-permissions:
	@echo "Securing file permissions..."
	@chmod +x scripts/secure-permissions.sh
	@bash scripts/secure-permissions.sh

init-db:
	@echo "Initializing agent database..."
	@if [ ! -f .env ]; then \
		echo "Error: .env file not found. Run 'make setup-env' first."; \
		exit 1; \
	fi
	python3 main.py init-db --config config.yaml

run: secure-permissions
	@echo "Starting API server..."
	@echo "Port: 8084"
	python3 main.py run --config config.yaml --log-level INFO

test:
	@echo "Running tests..."
	pytest tests/ -v --tb=short

security-audit:
	@echo "Scanning dependencies for known vulnerabilities..."
	@if ! command -v pip-audit &> /dev/null; then \
		echo "Installing pip-audit..."; \
		pip install pip-audit; \
	fi
	pip-audit -r requirements.txt

clean:
	@echo "Cleaning up..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "✓ Clean complete"
