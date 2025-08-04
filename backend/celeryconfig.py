# Celery configuration for rate limiting
import os

# Broker settings
broker_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
result_backend = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Task settings
task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'
timezone = 'UTC'
enable_utc = True

# Rate limiting
task_annotations = {
    'tasks.process_single_email': {
        'rate_limit': '10/s',  # Max 10 emails per second across all workers
    }
}