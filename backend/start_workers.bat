@echo off
echo Starting 4 Celery workers with dedicated models...

REM Start 4 workers in separate windows
start "Worker1 - gpt-3.5-turbo" cmd /k "celery -A tasks worker --loglevel=info --hostname=worker1@%%h --concurrency=1"
start "Worker2 - gpt-3.5-turbo-0125" cmd /k "celery -A tasks worker --loglevel=info --hostname=worker2@%%h --concurrency=1"
start "Worker3 - gpt-3.5-turbo-1106" cmd /k "celery -A tasks worker --loglevel=info --hostname=worker3@%%h --concurrency=1"
start "Worker4 - gpt-3.5-turbo-16k" cmd /k "celery -A tasks worker --loglevel=info --hostname=worker4@%%h --concurrency=1"

echo Workers started! Each worker uses a different model:
echo - Worker1: gpt-3.5-turbo
echo - Worker2: gpt-3.5-turbo-0125
echo - Worker3: gpt-3.5-turbo-1106
echo - Worker4: gpt-3.5-turbo-16k
echo.
echo Press any key to stop all workers...
pause

REM Kill all celery workers
taskkill /F /IM celery.exe
echo All workers stopped.