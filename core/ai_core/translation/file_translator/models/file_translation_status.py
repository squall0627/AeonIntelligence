from enum import Enum
from typing import Optional, Self

import redis
from pydantic import BaseModel

from api.db.redis_handler import get_redis


class Status(str, Enum):
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class FileTranslationStatus(BaseModel):
    task_id: str
    status: Status
    progress: int
    output_file_path: Optional[str] = None
    duration: Optional[float] = None
    error: Optional[str] = None

    @classmethod
    async def exists(
        cls, task_id: str, redis_client: redis.Redis = get_redis()
    ) -> bool:
        result = redis_client.hexists("translation_tasks", task_id)
        if isinstance(result, bool):
            return result
        else:
            return await result

    async def persist(self, redis_client: redis.Redis = get_redis()):
        result = redis_client.hset(
            "translation_tasks", self.task_id, self.model_dump_json()
        )
        if isinstance(result, int):
            pass
        else:
            await result

    @classmethod
    async def load(
        cls, task_id: str, redis_client: redis.Redis = get_redis()
    ) -> Optional[Self]:
        result = redis_client.hget("translation_tasks", task_id)
        if isinstance(result, Optional[str]):
            data = result
        else:
            data = await result
        if data:
            return FileTranslationStatus.model_validate_json(data)
        return None
