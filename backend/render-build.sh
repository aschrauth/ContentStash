#!/usr/bin/env bash
# Render.com build script for ContentStash backend
# This script installs Python dependencies and Playwright browser binaries
# System dependencies are automatically installed via render.yaml

set -o errexit  # Exit on error

echo "=== Installing Python dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Installing Playwright Chromium browser ==="
playwright install chromium

echo "=== Build completed successfully ==="