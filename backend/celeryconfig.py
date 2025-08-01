# Celery configuration for rate limiting
task_annotations = {
    'tasks.process_single_email': {
        'rate_limit': '10/s',  # Max 10 emails per second across all workers
    }
}