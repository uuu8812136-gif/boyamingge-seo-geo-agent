import json
from typing import Any

import redis

from app.core.config import get_settings

settings = get_settings()
_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def cache_get(key: str) -> Any | None:
    try:
        client = get_redis()
        value = client.get(key)
        if value is None:
            return None
        return json.loads(value)
    except (redis.RedisError, json.JSONDecodeError):
        return None


def cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    try:
        client = get_redis()
        client.set(key, json.dumps(value, ensure_ascii=False), ex=ttl or settings.intent_cache_ttl_seconds)
    except redis.RedisError:
        return


def cache_delete(*keys: str) -> None:
    if not keys:
        return
    try:
        get_redis().delete(*keys)
    except redis.RedisError:
        return
