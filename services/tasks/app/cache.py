import redis
import json
from typing import Any, Optional
import os

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=0,
    decode_responses=True
)

def set_cache(key: str, value: Any, expiration: int = 3600):
    """
    Set a key-value pair in the cache with expiration time in seconds.
    """
    redis_client.setex(key, expiration, json.dumps(value))

def get_cache(key: str) -> Optional[Any]:
    """
    Get a value from the cache by key.
    """
    value = redis_client.get(key)
    if value:
        return json.loads(value)
    return None

def delete_cache(key: str):
    """
    Delete a key-value pair from the cache.
    """
    redis_client.delete(key)