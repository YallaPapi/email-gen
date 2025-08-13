@echo off
echo ========================================
echo TWO-STEP EMAIL GENERATOR - STARTUP
echo ========================================
echo.

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.8+
    pause
    exit /b 1
)

REM Check for Redis
echo Checking for Redis...
redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo WARNING: Redis not running. Starting Redis...
    echo Please install Redis or use Docker: docker run -d -p 6379:6379 redis
    echo.
)

REM Install requirements if needed
echo Installing Python requirements...
pip install -q -r backend/requirements.txt 2>nul

REM Check for .env file
if not exist .env (
    echo.
    echo WARNING: .env file not found!
    echo Please create .env file with:
    echo   OPENAI_API_KEY=your-key-here
    echo   REDIS_URL=redis://localhost:6379/0
    echo.
    pause
)

REM Start services
echo.
echo Starting services...
echo ========================================

REM Start Celery workers in background
echo Starting Celery workers...
start /B celery -A backend.tasks worker --loglevel=info --concurrency=2 -n worker1@%%h
start /B celery -A backend.tasks worker --loglevel=info --concurrency=2 -n worker2@%%h

REM Wait a moment for workers to start
timeout /t 3 /nobreak >nul

REM Start Flask backend
echo Starting Flask backend...
start /B python backend/main.py

REM Wait for backend to start
timeout /t 2 /nobreak >nul

REM Open browser
echo.
echo ========================================
echo Services started successfully!
echo.
echo Web interface: http://localhost:5000
echo.
echo Press Ctrl+C to stop all services
echo ========================================

REM Keep script running
python -c "import time; time.sleep(86400)"