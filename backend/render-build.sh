#!/usr/bin/env bash
# Render.com build script for ContentStash backend
# This script installs Python dependencies and Playwright browser binaries
# System dependencies are automatically installed via render.yaml

set -o errexit  # Exit on error

echo "=== Installing Python dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Installing Playwright Chromium browser ==="
# Set Playwright browsers path to persist from build to runtime
# This is critical on Render.com where build and runtime environments are separate
export PLAYWRIGHT_BROWSERS_PATH=./ms-playwright-browsers
playwright install chromium

echo "Chromium installed successfully to $PLAYWRIGHT_BROWSERS_PATH"
echo "=== Build completed successfully ==="