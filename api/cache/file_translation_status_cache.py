from typing import Optional, Awaitable

import redis

from core.ai_core.translation.file_translator.models.file_translation_status import (
    FileTranslationStatus,
)

FILE_TRANSLATION_STATUS_CACHE_NAME = "file:translation:status"


class FileTranslationStatusCache:
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client

    def cache_key(self, user_id: str) -> str:
        return f"{FILE_TRANSLATION_STATUS_CACHE_NAME}:{user_id}"

    async def exists(self, user_id: str, task_id: str) -> bool:
        """Check if file translation status exists in Redis"""
        key = self.cache_key(user_id)
        result = self.redis_client.hexists(key, task_id)
        if isinstance(result, Awaitable):
            return await result
        else:
            return result

    async def get_status(
        self, user_id: str, task_id: str
    ) -> Optional[FileTranslationStatus]:
        """Get file translation status from Redis"""
        key = self.cache_key(user_id)
        result = self.redis_client.hget(key, task_id)
        if isinstance(result, Awaitable):
            data = await result
        else:
            data = result
        if data:
            return FileTranslationStatus.model_validate_json(data)
        return None

    async def get_all_status(
        self, user_id: str
    ) -> Optional[dict[str, FileTranslationStatus]]:
        """Get all file translation status of specified user from Redis"""
        key = self.cache_key(user_id)
        result = self.redis_client.hgetall(key)
        if isinstance(result, Awaitable):
            data = await result
        else:
            data = result
        if data:
            return {
                task_id: FileTranslationStatus.model_validate_json(status)
                for task_id, status in data.items()
            }
        return None

    async def set_status(self, user_id: str, status: FileTranslationStatus):
        """Set file translation status in Redis with expiration (default 24 hours)"""
        key = self.cache_key(user_id)
        result = self.redis_client.hset(key, status.task_id, status.model_dump_json())
        if isinstance(result, Awaitable):
            await result
        else:
            pass

    async def delete_status(self, user_id: str, task_id: str):
        key = self.cache_key(user_id)
        result = self.redis_client.hdel(key, task_id)
        if isinstance(result, Awaitable):
            await result
        else:
            pass
