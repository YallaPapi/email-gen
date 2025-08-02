import os
from celery import current_task

class WorkerModelAssigner:
    """Assigns a specific OpenAI model to each worker based on worker ID/hostname"""
    
    def __init__(self):
        # Map worker names/IDs to specific models
        self.model_assignments = {
            "worker1": "gpt-3.5-turbo",
            "worker2": "gpt-3.5-turbo-0125", 
            "worker3": "gpt-3.5-turbo-1106",
            "worker4": "gpt-3.5-turbo-16k"
        }
        
        # Default models list for round-robin if worker not in assignments
        self.models = [
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-0125",
            "gpt-3.5-turbo-1106",
            "gpt-3.5-turbo-16k"
        ]
    
    def get_worker_model(self):
        """Get the model assigned to current worker"""
        # Try to get worker hostname/name
        if current_task and hasattr(current_task.request, 'hostname'):
            worker_name = current_task.request.hostname
            
            # Extract worker number if hostname is like "celery@worker1"
            if '@' in worker_name:
                worker_id = worker_name.split('@')[1]
            else:
                worker_id = worker_name
                
            # Check if we have a specific assignment
            if worker_id in self.model_assignments:
                return self.model_assignments[worker_id]
                
            # Try to extract number and use as index
            try:
                # Handle names like "worker1", "worker-1", "celery-worker-1"
                import re
                match = re.search(r'(\d+)', worker_id)
                if match:
                    worker_num = int(match.group(1))
                    # Use modulo to ensure we stay within bounds
                    model_index = (worker_num - 1) % len(self.models)
                    return self.models[model_index]
            except:
                pass
        
        # Fallback: use process ID for consistent model per worker
        pid = os.getpid()
        model_index = pid % len(self.models)
        return self.models[model_index]