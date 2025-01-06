import json
from typing import Optional, Awaitable

import redis

USER_SETTINGS_CACHE_KEY = "user:settings"


class UserSettingsCache:
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client

    def cache_key(self, user_id: str) -> str:
        return f"{USER_SETTINGS_CACHE_KEY}:{user_id}"

    async def get_user_settings(self, user_id: str) -> Optional[dict]:
        """Get user settings from Redis"""
        key = self.cache_key(user_id)
        result = self.redis_client.get(key)
        if isinstance(result, Awaitable):
            data = await result
        else:
            data = result
        return json.loads(data) if data else None

    async def set_user_settings(self, user_id: str, settings: dict):
        """Set user settings in Redis with expiration (default 24 hours)"""
        key = self.cache_key(user_id)
        result = self.redis_client.set(key, json.dumps(settings))
        if isinstance(result, Awaitable):
            await result
        else:
            pass
