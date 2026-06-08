#!/bin/bash

# Secure file permissions for production deployment
# This script should be run as the application user

set -e

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"

echo "Setting secure file permissions..."

# Set config file permissions to 600 (user read/write only)
if [ -f "config.yaml" ]; then
    chmod 600 config.yaml
    echo "✓ config.yaml: 600"
fi

# Set .env file permissions to 600
if [ -f ".env" ]; then
    chmod 600 .env
    echo "✓ .env: 600"
fi

# Set .env.example permissions to 644 (readable by all, but not writable)
if [ -f ".env.example" ]; then
    chmod 644 .env.example
    echo "✓ .env.example: 644"
fi

# Create logs directory if it doesn't exist
if [ ! -d "logs" ]; then
    mkdir -p logs
    chmod 700 logs
    echo "✓ logs/ directory created with 700 permissions"
else
    chmod 700 logs
    echo "✓ logs/: 700"
fi

# Ensure audit log is restricted (if it exists)
if [ -f "logs/audit.log" ]; then
    chmod 600 logs/audit.log
    echo "✓ logs/audit.log: 600"
fi

# Set private key files to 600 if they exist
if [ -f ".ssh/id_rsa" ]; then
    chmod 600 .ssh/id_rsa
    echo "✓ .ssh/id_rsa: 600"
fi

echo ""
echo "All file permissions have been secured!"
echo ""
echo "Verification:"
ls -la config.yaml .env .env.example 2>/dev/null | awk '{print $1, $NF}' || true
