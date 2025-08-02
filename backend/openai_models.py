import redis
from datetime import datetime

class OpenAIModelRotator:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.models = [
            "gpt-3.5-turbo",           # Cheapest, current default
            "gpt-3.5-turbo-0125",      # Latest 3.5 version
            "gpt-3.5-turbo-1106",      # Stable older version
            "gpt-3.5-turbo-16k"        # Larger context if needed
        ]
        self.daily_limit = 5  # Set to 5 for testing rotation
        
    def get_available_model(self):
        """Get next available model under daily limit"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        for model in self.models:
            key = f"openai_requests:{model}:{today}"
            count = int(self.redis.get(key) or 0)
            
            if count < self.daily_limit:
                return model
                
        return None  # All models exhausted
        
    def increment_usage(self, model):
        """Track model usage and auto-expire after 24h"""
        today = datetime.now().strftime("%Y-%m-%d")
        key = f"openai_requests:{model}:{today}"
        self.redis.incr(key)
        self.redis.expire(key, 86400)  # Expire after 24 hours
        
    def get_usage_stats(self):
        """Get current usage for all models"""
        today = datetime.now().strftime("%Y-%m-%d")
        stats = {}
        
        for model in self.models:
            key = f"openai_requests:{model}:{today}"
            count = int(self.redis.get(key) or 0)
            stats[model] = {
                "used": count,
                "remaining": self.daily_limit - count
            }
            
        return stats