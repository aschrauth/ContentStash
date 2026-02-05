#!/usr/bin/env bash

# Convenience script to run the backend using the virtual environment

# Ensure we are in the backend directory
cd "$(dirname "$0")"

# Activate the virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the backend
python3 main.py
