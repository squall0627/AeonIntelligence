import json

import redis
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.auth.oauth2 import User, get_current_user
from api.cache.user_settings_cache import UserSettingsCache
from api.db.dao.user_settings_dao import UserSettingsDao
from api.db.database import get_db
from api.cache.redis_handler import get_redis
from core.utils.log_handler import rotating_file_logger

logger = rotating_file_logger("user_settings_api")

router = APIRouter()


async def get_user_settings_with_cache(user_id: str, dao, redis_client) -> dict:
    """Get user settings with Redis cache"""
    cache = UserSettingsCache(redis_client)
    # Try to get from cache first
    settings = await cache.get_user_settings(user_id)
    logger.debug(">>> Settings from cache:", settings)

    if settings is None:
        logger.debug(">>> Settings not found in cache")
        # If not in cache, get from DB
        settings = await dao.get_user_settings(user_id)
        if settings is None:
            # If not in db, save a default settings
            settings = {"dark_mode": False}
            await dao.update_user_settings(user_id, **settings)
            logger.debug(">>> No settings found, saved default settings")
        # Store in cache
        await cache.set_user_settings(user_id, settings)
        logger.debug(">>> Settings saved to cache")

    return settings


@router.get("/theme")
async def get_theme_settings(
    current_user: User = Depends(get_current_user),
    redis_client: redis.Redis = Depends(get_redis),
    db: Session = Depends(get_db),
):
    """Get user's theme settings"""
    dao = UserSettingsDao(db)
    return await get_user_settings_with_cache(current_user.email, dao, redis_client)


@router.post("/theme")
async def update_theme_settings(
    settings: dict,
    current_user: User = Depends(get_current_user),
    redis_client: redis.Redis = Depends(get_redis),
    db: Session = Depends(get_db),
):
    """Update user's theme settings"""
    # Update DB
    dao = UserSettingsDao(db)
    await dao.update_user_settings(current_user.email, **settings)
    logger.info(
        f"User {current_user.email} updated theme settings: {json.dumps(settings)}"
    )
    # Update cache
    cache = UserSettingsCache(redis_client)
    await cache.set_user_settings(current_user.email, settings)
    return {"status": "success"}
