#!/bin/bash

# Create data directory if it doesn't exist
mkdir -p ./data

# Install dependencies
pip install -r requirements.txt

# Start the application
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
