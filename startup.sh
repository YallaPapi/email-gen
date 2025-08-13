#!/bin/bash

echo "========================================"
echo "TWO-STEP EMAIL GENERATOR - STARTUP"
echo "========================================"
echo ""

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python not found. Please install Python 3.8+"
    exit 1
fi

# Check for Redis
echo "Checking for Redis..."
if ! redis-cli ping &> /dev/null; then
    echo "WARNING: Redis not running."
    echo "Please start Redis with: redis-server"
    echo "Or use Docker: docker run -d -p 6379:6379 redis"
    echo ""
fi

# Install requirements
echo "Installing Python requirements..."
pip install -q -r backend/requirements.txt 2>/dev/null

# Check for .env file
if [ ! -f .env ]; then
    echo ""
    echo "WARNING: .env file not found!"
    echo "Please create .env file with:"
    echo "  OPENAI_API_KEY=your-key-here"
    echo "  REDIS_URL=redis://localhost:6379/0"
    echo ""
    read -p "Press enter to continue..."
fi

# Start services
echo ""
echo "Starting services..."
echo "========================================"

# Start Celery workers in background
echo "Starting Celery workers..."
celery -A backend.tasks worker --loglevel=info --concurrency=2 -n worker1@%h &
celery -A backend.tasks worker --loglevel=info --concurrency=2 -n worker2@%h &

# Wait for workers
sleep 3

# Start Flask backend
echo "Starting Flask backend..."
python3 backend/main.py &

# Wait for backend
sleep 2

echo ""
echo "========================================"
echo "Services started successfully!"
echo ""
echo "Web interface: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop all services"
echo "========================================"

# Wait indefinitely
wait