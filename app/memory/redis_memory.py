import redis
import json
import os
from typing import List, Dict

# Parse REDIS_URL from .env or default (Updated connection state)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

class CitizenMemory:
    """
    Tracks the recent 5 grievances for a citizen in Redis for context window injection.
    """
    def __init__(self):
        try:
            self.client = redis.from_url(REDIS_URL, decode_responses=True)
            self.client.ping()
        except redis.ConnectionError:
            print("Warning: Redis connection failed. Citizen memory will be disabled.")
            self.client = None

    def add_grievance(self, citizen_id: str, category: str, description: str, urgency: str = "UNKNOWN"):
        """Stores a summarized grievance in the citizen's recent memory list."""
        if not self.client:
            return

        key = f"citizen_memory:{citizen_id}"
        entry = {
            "category": category,
            "description": description[:100] + "..." if len(description) > 100 else description,
            "urgency": urgency
        }
        
        # Add to left of list
        self.client.lpush(key, json.dumps(entry))
        
        # Keep only last 5 grievances
        self.client.ltrim(key, 0, 4)
        
        # Expire after 30 days (2592000 seconds)
        self.client.expire(key, 2592000)

    def get_recent_grievances(self, citizen_id: str) -> List[Dict]:
        """Retrieves the recent grievances for the given citizen."""
        if not self.client:
            return []
            
        key = f"citizen_memory:{citizen_id}"
        items = self.client.lrange(key, 0, 4)
        return [json.loads(item) for item in items]

# Singleton instance
memory_store = CitizenMemory()
