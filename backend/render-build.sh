#!/usr/bin/env bash
# Render.com build script for ContentStash backend
# This script installs Python dependencies and Playwright browser binaries

set -o errexit  # Exit on error

echo "=== Installing Python dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Installing Playwright browser binaries ==="
playwright install chromium

echo "=== Installing system dependencies for Chromium ==="
# Note: Render.com uses Ubuntu-based containers
# These dependencies are required for Chromium to run in headless mode
# They should be configured in the Render.com dashboard under "Native Environment"
echo "Required system packages (configure in Render dashboard):"
echo "  - libnss3"
echo "  - libatk1.0-0"
echo "  - libatk-bridge2.0-0"
echo "  - libcups2"
echo "  - libdrm2"
echo "  - libxkbcommon0"
echo "  - libxcomposite1"
echo "  - libxdamage1"
echo "  - libxfixes3"
echo "  - libxrandr2"
echo "  - libgbm1"
echo "  - libasound2"

echo "=== Build completed successfully ==="