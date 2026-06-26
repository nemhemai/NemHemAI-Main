import os
import json
import redis
from typing import Optional, Any

# Parse REDIS_URL from .env or default (Updated connection state)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

class RedisQueryCache:
    """
    Caches document query results in Redis to reduce redundant RAG pipelines and LLM inference.
    """
    def __init__(self):
        try:
            self.client = redis.from_url(REDIS_URL, decode_responses=True)
            self.client.ping()
        except redis.ConnectionError:
            print("Warning: Redis connection failed. Query cache will be disabled.")
            self.client = None

    def _get_key(self, query: str) -> str:
        # Normalize the query string to ignore case, leading/trailing whitespace
        normalized = " ".join(query.strip().lower().split())
        return f"query_cache:{normalized}"

    def get(self, query: str) -> Optional[dict]:
        """
        Retrieve cached result for a query if it exists.
        """
        if not self.client:
            return None
        
        key = self._get_key(query)
        try:
            cached_val = self.client.get(key)
            if cached_val:
                return json.loads(cached_val)
        except Exception as e:
            print(f"Error reading from Redis query cache: {e}")
        return None

    def set(self, query: str, result: dict, expire_seconds: int = 3600) -> None:
        """
        Cache the query result in Redis with an expiration TTL.
        """
        if not self.client:
            return
        
        key = self._get_key(query)
        try:
            self.client.set(key, json.dumps(result), ex=expire_seconds)
        except Exception as e:
            print(f"Error writing to Redis query cache: {e}")

# Singleton cache instance
query_cache = RedisQueryCache()

import hashlib

class RedisRetrievalCache:
    """
    Caches the retrieved and reranked chunks for a query + intent to bypass database and ColBERT.
    """
    def __init__(self):
        try:
            self.client = redis.from_url(REDIS_URL, decode_responses=True)
            self.client.ping()
        except redis.ConnectionError:
            self.client = None

    def _get_key(self, query: str, query_type: str) -> str:
        normalized = " ".join(query.strip().lower().split())
        query_hash = hashlib.sha256(normalized.encode('utf-8')).hexdigest()
        return f"retrieval_cache:{query_type}:{query_hash}"

    def get(self, query: str, query_type: str) -> Optional[list[dict]]:
        if not self.client:
            return None
        key = self._get_key(query, query_type)
        try:
            cached_val = self.client.get(key)
            if cached_val:
                return json.loads(cached_val)
        except Exception as e:
            print(f"Error reading from Redis retrieval cache: {e}")
        return None

    def set(self, query: str, query_type: str, chunks: list[dict], expire_hours: int = 24) -> None:
        if not self.client:
            return
        key = self._get_key(query, query_type)
        try:
            self.client.set(key, json.dumps(chunks), ex=expire_hours * 3600)
        except Exception as e:
            print(f"Error writing to Redis retrieval cache: {e}")

retrieval_cache = RedisRetrievalCache()
