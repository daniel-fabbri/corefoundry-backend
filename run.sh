#!/bin/bash
# run.sh - Start the CoreFoundry server

# Set the working directory to the script location
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the FastAPI application
echo "Starting CoreFoundry server..."
python -m corefoundry.main
