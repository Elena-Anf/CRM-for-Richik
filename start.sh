#!/bin/bash
# Start script for Timeweb hosting
# Install dependencies
pip install -r requirements.txt --quiet

# Run database migrations (if needed)
# alembic upgrade head

# Start the app
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
