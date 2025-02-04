from typing import Optional, Awaitable

import redis

from core.ai_core.translation.file_translator.models.file_translation_status import (
    FileTranslationStatus,
)

FILE_TRANSLATION_STATUS_CACHE_NAME = "file:translation:status"


class FileTranslationStatusCache:
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client

    async def get_status(self, task_id: str) -> Optional[FileTranslationStatus]:
        """Get file translation status from Redis"""
        result = self.redis_client.hget(FILE_TRANSLATION_STATUS_CACHE_NAME, task_id)
        if isinstance(result, Awaitable):
            data = await result
        else:
            data = result
        if data:
            return FileTranslationStatus.model_validate_json(data)
        return None

    async def set_status(self, status: FileTranslationStatus):
        """Set file translation status in Redis with expiration (default 24 hours)"""
        result = self.redis_client.hset(
            FILE_TRANSLATION_STATUS_CACHE_NAME, status.task_id, status.model_dump_json()
        )
        if isinstance(result, Awaitable):
            await result
        else:
            pass

    async def delete_status(self, task_id: str):
        result = self.redis_client.hdel(FILE_TRANSLATION_STATUS_CACHE_NAME, task_id)
        if isinstance(result, Awaitable):
            await result
        else:
            pass
