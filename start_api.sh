#!/bin/bash
# Start script for SQL Agent API with LLM provider support
# This script loads environment variables from .env and starts the API

set -e

cd "$(dirname "$0")"

echo "Starting SQL Agent API..."

# Load and export environment variables from .env
if [ -f .env ]; then
  echo "Loading API keys from .env..."
  export $(grep -v '^#' .env | xargs)
fi

# Verify API keys
if [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$GOOGLE_API_KEY" ] && [ -z "$OPENAI_API_KEY" ]; then
  echo "⚠️  Warning: No LLM API key configured"
  echo "   Edit .env and set one of:"
  echo "     ANTHROPIC_API_KEY=sk-ant-..."
  echo "     GOOGLE_API_KEY=AIzaSy..."
  echo "     OPENAI_API_KEY=sk-..."
else
  echo "✓ API key loaded"
fi

# Activate virtual environment and start
source venv/bin/activate
exec python3 main.py run --config config.yaml
