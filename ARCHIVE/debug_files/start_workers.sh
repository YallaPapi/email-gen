#!/bin/bash
echo "Starting 4 Celery workers with dedicated models..."

# Start 4 workers in background
celery -A tasks worker --loglevel=info --hostname=worker1@%h --concurrency=1 &
WORKER1_PID=$!

celery -A tasks worker --loglevel=info --hostname=worker2@%h --concurrency=1 &
WORKER2_PID=$!

celery -A tasks worker --loglevel=info --hostname=worker3@%h --concurrency=1 &
WORKER3_PID=$!

celery -A tasks worker --loglevel=info --hostname=worker4@%h --concurrency=1 &
WORKER4_PID=$!

echo "Workers started with PIDs: $WORKER1_PID, $WORKER2_PID, $WORKER3_PID, $WORKER4_PID"
echo "Each worker uses a different model:"
echo "- Worker1: gpt-3.5-turbo"
echo "- Worker2: gpt-3.5-turbo-0125"
echo "- Worker3: gpt-3.5-turbo-1106"
echo "- Worker4: gpt-3.5-turbo-16k"
echo ""
echo "Press Enter to stop all workers..."
read

# Kill all workers
kill $WORKER1_PID $WORKER2_PID $WORKER3_PID $WORKER4_PID
echo "All workers stopped."