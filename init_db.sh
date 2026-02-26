#!/bin/bash
# init_db.sh - Initialize the database

# Set the working directory to the script location
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Create a Python script to initialize the database
python -c "
from corefoundry.app.db.connection import init_db
print('Initializing database...')
init_db()
print('Database initialized successfully!')
"
