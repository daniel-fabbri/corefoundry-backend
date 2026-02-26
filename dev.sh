#!/bin/bash
# dev.sh - Start the server in development mode with hot reload

# Set the working directory to the script location
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run with uvicorn in reload mode
echo "Starting CoreFoundry in development mode with hot reload..."
uvicorn corefoundry.main:app --reload --host 0.0.0.0 --port 8000
