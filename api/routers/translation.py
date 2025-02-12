import asyncio
import json
import os
import tempfile
from pathlib import Path

import redis
import stopwatch

from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    HTTPException,
    BackgroundTasks,
    Form,
)
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from sqlalchemy.orm import Session

from api.auth.oauth2 import get_current_user, User
from api.cache.file_translation_status_cache import FileTranslationStatusCache
from api.cache.redis_handler import get_redis
from api.db.dao.file_translation_history_dao import FileTranslationHistoryDao
from api.db.database import get_db
from core.ai_core.translation.file_translator.models.file_translation_status import (
    FileTranslationStatus,
    Status,
)
from core.ai_core.translation.language import Language
from core.ai_core.translation.file_translator.file_translator_builder import (
    FileTranslatorBuilder,
)
from core.ai_core.translation.text_translator import TextTranslator
from core.utils.log_handler import rotating_file_logger
from api.middleware import auth_middleware

from dotenv import load_dotenv

load_dotenv()

logger = rotating_file_logger("translation_api")


router = APIRouter()


# Pydantic models for request/response
class TextTranslationRequest(BaseModel):
    text: str
    is_stream: Optional[bool] = False
    source_language: Optional[Language] = None
    target_language: Optional[Language] = None
    keywords_map: Optional[dict] = None


class TranslationResponse(BaseModel):
    translated_text: str
    duration: Optional[float] = None


# Temp directory to save uploaded and translated files
UPLOAD_FOLDER = "translation/original"
TRANSLATED_FOLDER = "translation/translated"


@router.post("/text", response_model=TranslationResponse)
async def translate_text(
    params: TextTranslationRequest,
    credentials: dict = Depends(auth_middleware),
):
    logger.debug("credentials: " + str(credentials))

    logger.info("translate text endpoint called")
    try:
        input_text = params.text
        logger.debug(f"Input text: {input_text}")
        source_language = params.source_language
        logger.debug(f"Source language: {source_language}")
        target_language = params.target_language
        logger.debug(f"Target language: {target_language}")
        keywords_map = params.keywords_map if params.keywords_map else {}
        logger.debug(f"Keywords map: {keywords_map}")

        translator = TextTranslator(source_language, target_language, keywords_map)

        if not params.is_stream:
            sw = stopwatch.Stopwatch()
            sw.start()

            translated_text = translator.translate(input_text)

            sw.stop()

            logger.info(f"Translated text: {translated_text}")
            return TranslationResponse(
                translated_text=translated_text,
                duration=sw.duration,
            )
        else:
            return StreamingResponse(
                translator.astream_translate(input_text), media_type="text/event-stream"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/text/ja_to_zh", response_model=TranslationResponse)
async def translate_text_ja_to_zh(
    params: TextTranslationRequest,
    credentials: dict = Depends(auth_middleware),
):
    logger.debug("credentials: " + str(credentials))
    logger.info("translate text ja_to_zh endpoint called")
    params.source_language = Language.JAPANESE
    params.target_language = Language.CHINESE
    return await translate_text(params, credentials)


@router.post("/text/ja_to_en", response_model=TranslationResponse)
async def translate_text_ja_to_en(
    params: TextTranslationRequest,
    credentials: dict = Depends(auth_middleware),
):
    logger.debug("credentials: " + str(credentials))
    logger.info("translate text ja_to_en endpoint called")
    params.source_language = Language.JAPANESE
    params.target_language = Language.ENGLISH
    return await translate_text(params, credentials)


@router.post("/text/zh_to_ja", response_model=TranslationResponse)
async def translate_text_zh_to_ja(
    params: TextTranslationRequest,
    credentials: dict = Depends(auth_middleware),
):
    logger.debug("credentials: " + str(credentials))
    logger.info("translate text zh_to_ja endpoint called")
    params.source_language = Language.CHINESE
    params.target_language = Language.JAPANESE
    return await translate_text(params, credentials)


@router.post("/text/zh_to_en", response_model=TranslationResponse)
async def translate_text_zh_to_en(
    params: TextTranslationRequest,
    credentials: dict = Depends(auth_middleware),
):
    logger.debug("credentials: " + str(credentials))
    logger.info("translate text zh_to_en endpoint called")
    params.source_language = Language.CHINESE
    params.target_language = Language.ENGLISH
    return await translate_text(params, credentials)


@router.post("/text/en_to_ja", response_model=TranslationResponse)
async def translate_text_en_to_ja(
    params: TextTranslationRequest,
    credentials: dict = Depends(auth_middleware),
):
    logger.debug("credentials: " + str(credentials))
    logger.info("translate text en_to_ja endpoint called")
    params.source_language = Language.ENGLISH
    params.target_language = Language.JAPANESE
    return await translate_text(params, credentials)


@router.post("/text/en_to_zh", response_model=TranslationResponse)
async def translate_text_en_to_zh(
    params: TextTranslationRequest,
    credentials: dict = Depends(auth_middleware),
):
    logger.debug("credentials: " + str(credentials))
    logger.info("translate text en_to_zh endpoint called")
    params.source_language = Language.ENGLISH
    params.target_language = Language.CHINESE
    return await translate_text(params, credentials)


@router.post("/file")
async def translate_file(
    background_tasks: BackgroundTasks,
    params: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    credentials: dict = Depends(auth_middleware),
    redis_client: redis.Redis = Depends(get_redis),
):
    logger.debug("credentials: " + str(credentials))
    logger.info("translate file endpoint called")
    try:
        params = json.loads(params)
        source_language = params["source_language"]
        logger.debug(f"Source language: {source_language}")
        target_language = params["target_language"]
        logger.debug(f"Target language: {target_language}")
        keywords_map = params["keywords_map"] if "keywords_map" in params else {}
        logger.debug(f"Keywords map: {keywords_map}")
        kwargs = params["kwargs"] if "kwargs" in params else {}
        logger.debug(f"Kwargs: {kwargs}")
        is_stream = params["is_stream"] if "is_stream" in params else False
        logger.debug(f"Is stream: {is_stream}")

        # Get user_id from credentials
        user_id = current_user.email

        # Create unique task ID
        task_id = f"{datetime.now().timestamp()}_{file.filename}"

        # Ensure the uploaded file has a safe and valid name
        # filename = secure_filename(file.filename)
        filename = file.filename

        # Save the uploaded file to a temporary system location
        temp_dir = os.getenv("TEMP_PATH", tempfile.gettempdir())
        input_dir = os.path.join(temp_dir, UPLOAD_FOLDER)
        os.makedirs(input_dir, exist_ok=True)
        input_file_path = os.path.join(input_dir, filename)
        with open(input_file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        logger.info(f"Uploaded file saved to: {input_file_path}")

        # Initialize translation status
        status = FileTranslationStatus(
            task_id=task_id,
            task_name=f"{source_language}➡︎{target_language}",
            input_file_path=input_file_path,
            status=Status.PROCESSING,
            progress=0,
        )

        status_cache = FileTranslationStatusCache(redis_client)
        await status_cache.set_status(user_id, status)
        logger.info("Redis status persisted OK")

        # Process translation
        if not is_stream:
            logger.info("Processing translation as non-streaming")

            # Add translation task to background tasks
            background_tasks.add_task(
                process_file_translation_stream,
                status_cache,
                user_id,
                status,
                input_file_path,
                source_language,
                target_language,
                keywords_map,
                **kwargs,
            )

            logger.info("background_tasks.add_task OK")

            return {"task_id": task_id}
        else:
            logger.info("Processing translation as streaming")

            # Create file translator
            file_translator = FileTranslatorBuilder.build_file_translator(
                input_file_path,
                source_language,
                target_language,
                status=status,
                keywords_map=keywords_map,
                kwargs=kwargs,
            )

            # Set up the output path for the translated file
            temp_dir = os.getenv("TEMP_PATH", tempfile.gettempdir())
            output_dir = os.path.join(temp_dir, TRANSLATED_FOLDER)
            os.makedirs(output_dir, exist_ok=True)

            return StreamingResponse(
                astream_translate(file_translator, output_dir, status_cache, user_id),
                media_type="text/event-stream",
            )

        # TODO
        # delete temp file
        # finally:
        #     # Cleanup temporary file
        #     if status.status == Status.COMPLETED or status.status == Status.ERROR:
        #         if os.path.exists(input_file_path):
        #             os.remove(input_file_path)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def astream_translate(
    file_translator,
    output_dir: Path | str,
    status_cache: FileTranslationStatusCache,
    user_id: str,
):
    async for status in file_translator.astream_translate(output_dir):
        await status_cache.set_status(user_id, status)
        yield status.model_dump_json()
        await asyncio.sleep(0.01)


@router.post("/file/ja_to_zh")
async def translate_file_ja_to_zh(
    background_tasks: BackgroundTasks,
    params: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    credentials: dict = Depends(auth_middleware),
    redis_client: redis.Redis = Depends(get_redis),
):
    logger.debug("credentials: " + str(credentials))
    logger.debug(f"Params: {params}")
    logger.info("translate file ja_to_zh endpoint called")

    source_language = Language.JAPANESE
    target_language = Language.CHINESE

    params = json.loads(params)
    params.update(
        {"source_language": source_language, "target_language": target_language}
    )

    params = json.dumps(params)
    return await translate_file(
        background_tasks, params, file, current_user, credentials, redis_client
    )


@router.post("/file/ja_to_en")
async def translate_file_ja_to_en(
    background_tasks: BackgroundTasks,
    params: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    credentials: dict = Depends(auth_middleware),
    redis_client: redis.Redis = Depends(get_redis),
):
    logger.debug("credentials: " + str(credentials))
    logger.debug(f"Params: {params}")
    logger.info("translate file ja_to_en endpoint called")

    source_language = Language.JAPANESE
    target_language = Language.ENGLISH

    params = json.loads(params)
    params.update(
        {"source_language": source_language, "target_language": target_language}
    )

    params = json.dumps(params)
    return await translate_file(
        background_tasks, params, file, current_user, credentials, redis_client
    )


@router.post("/file/zh_to_ja")
async def translate_file_zh_to_ja(
    background_tasks: BackgroundTasks,
    params: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    credentials: dict = Depends(auth_middleware),
    redis_client: redis.Redis = Depends(get_redis),
):
    logger.debug("credentials: " + str(credentials))
    logger.debug(f"Params: {params}")
    logger.info("translate file zh_to_ja endpoint called")

    source_language = Language.CHINESE
    target_language = Language.JAPANESE

    params = json.loads(params)
    params.update(
        {"source_language": source_language, "target_language": target_language}
    )

    params = json.dumps(params)
    return await translate_file(
        background_tasks, params, file, current_user, credentials, redis_client
    )


@router.post("/file/zh_to_en")
async def translate_file_zh_to_en(
    background_tasks: BackgroundTasks,
    params: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    credentials: dict = Depends(auth_middleware),
    redis_client: redis.Redis = Depends(get_redis),
):
    logger.debug("credentials: " + str(credentials))
    logger.debug(f"Params: {params}")
    logger.info("translate file zh_to_en endpoint called")

    source_language = Language.CHINESE
    target_language = Language.ENGLISH

    params = json.loads(params)
    params.update(
        {"source_language": source_language, "target_language": target_language}
    )

    params = json.dumps(params)
    return await translate_file(
        background_tasks, params, file, current_user, credentials, redis_client
    )


@router.post("/file/en_to_ja")
async def translate_file_en_to_ja(
    background_tasks: BackgroundTasks,
    params: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    credentials: dict = Depends(auth_middleware),
    redis_client: redis.Redis = Depends(get_redis),
):
    logger.debug("credentials: " + str(credentials))
    logger.debug(f"Params: {params}")
    logger.info("translate file en_to_ja endpoint called")

    source_language = Language.ENGLISH
    target_language = Language.JAPANESE

    params = json.loads(params)
    params.update(
        {"source_language": source_language, "target_language": target_language}
    )

    params = json.dumps(params)
    return await translate_file(
        background_tasks, params, file, current_user, credentials, redis_client
    )


@router.post("/file/en_to_zh")
async def translate_file_en_to_zh(
    background_tasks: BackgroundTasks,
    params: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    credentials: dict = Depends(auth_middleware),
    redis_client: redis.Redis = Depends(get_redis),
):
    logger.debug("credentials: " + str(credentials))
    logger.debug(f"Params: {params}")
    logger.info("translate file en_to_zh endpoint called")

    source_language = Language.ENGLISH
    target_language = Language.CHINESE

    params = json.loads(params)
    params.update(
        {"source_language": source_language, "target_language": target_language}
    )

    params = json.dumps(params)
    return await translate_file(
        background_tasks, params, file, current_user, credentials, redis_client
    )


@router.get("/status", response_model=FileTranslationStatus)
async def get_translation_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
    credentials: dict = Depends(auth_middleware),
    redis_client: redis.Redis = Depends(get_redis),
):
    logger.debug("credentials: " + str(credentials))
    logger.info("get translation status endpoint called")

    # Get user_id from credentials
    user_id = current_user.email

    status_cache = FileTranslationStatusCache(redis_client)
    if not await status_cache.exists(user_id, task_id):
        logger.error(f"Task ID {task_id} not found")
        raise HTTPException(status_code=404, detail="Task not found")
    return await status_cache.get_status(user_id, task_id)


@router.get("/status/all")
async def get_all_translation_status(
    current_user: User = Depends(get_current_user),
    credentials: dict = Depends(auth_middleware),
    redis_client: redis.Redis = Depends(get_redis),
):
    logger.debug("credentials: " + str(credentials))
    logger.info("get all translation status endpoint called")

    # Get user_id from credentials
    user_id = current_user.email

    status_cache = FileTranslationStatusCache(redis_client)
    result = await status_cache.get_all_status(user_id)
    return result if result else {}


@router.get("/download")
async def download_translated_file(
    task_id: str,
    credentials: dict = Depends(auth_middleware),
    db: Session = Depends(get_db),
):
    logger.debug("credentials: " + str(credentials))
    logger.info("download translated file endpoint called")

    # # Get user_id from credentials
    # user_id = current_user.email
    #
    # status_cache = FileTranslationStatusCache(redis_client)
    # if not await status_cache.exists(user_id, task_id):
    #     logger.error(f"Task ID {task_id} not found")
    #     raise HTTPException(
    #         status_code=404, detail=f"Task not found. Task ID: {task_id}"
    #     )
    #
    # task = await status_cache.get_status(user_id, task_id)
    # if task.status != Status.COMPLETED:
    #     logger.error(f"Task ID {task_id} not completed")
    #     raise HTTPException(
    #         status_code=400, detail=f"Translation not completed. Task ID: {task_id}"
    #     )
    #
    # if not task.output_file_path or not os.path.exists(task.output_file_path):
    #     logger.error(f"File not found: {task.output_file_path}")
    #     raise HTTPException(
    #         status_code=404, detail=f"File not found: {task.output_file_path}"
    #     )

    # Get translation history by task_id
    dao = FileTranslationHistoryDao(db)
    history = await dao.get_by_task_id(task_id)
    if not history:
        logger.error(f"Translation history not found for task_id: {task_id}")
        raise HTTPException(
            status_code=404,
            detail=f"Translation history not found for task_id: {task_id}",
        )

    return FileResponse(
        history.translated_file_path, filename=history.translated_file_name
    )


def process_file_translation(
    status: FileTranslationStatus,
    file_path: str,
    source_language: Language,
    target_language: Language,
    keywords_map,
    **kwargs,
):
    try:
        # Create file translator
        file_translator = FileTranslatorBuilder.build_file_translator(
            file_path,
            source_language,
            target_language,
            status=status,
            keywords_map=keywords_map,
            kwargs=kwargs,
        )

        # Set up the output path for the translated file
        temp_dir = os.getenv("TEMP_PATH", tempfile.gettempdir())
        output_dir = os.path.join(temp_dir, TRANSLATED_FOLDER)
        os.makedirs(output_dir, exist_ok=True)

        # Process translation
        status = file_translator.translate(output_dir)

    except Exception as e:
        logger.error(f"process_file_translation Error: {str(e)}")
        # Update status to error
        status.status = Status.ERROR
        status.error = str(e)

    finally:
        # Cleanup temporary file
        if os.path.exists(file_path):
            os.remove(file_path)


async def process_file_translation_stream(
    status_cache: FileTranslationStatusCache,
    user_id: str,
    status: FileTranslationStatus,
    input_file_path: str,
    source_language: Language,
    target_language: Language,
    keywords_map,
    **kwargs,
):
    # Create file translator
    file_translator = FileTranslatorBuilder.build_file_translator(
        input_file_path,
        source_language,
        target_language,
        status=status,
        keywords_map=keywords_map,
        kwargs=kwargs,
    )

    # Set up the output path for the translated file
    temp_dir = os.getenv("TEMP_PATH", tempfile.gettempdir())
    output_dir = os.path.join(temp_dir, TRANSLATED_FOLDER)
    os.makedirs(output_dir, exist_ok=True)

    async for status in file_translator.astream_translate(output_dir):
        await status_cache.set_status(user_id, status)
        await asyncio.sleep(0.01)


# File translation history response model
class FileTranslationHistoryResponse(BaseModel):
    id: int
    user_id: str
    task_id: str
    task_name: str
    date_time: datetime
    source_file_name: str
    source_file_path: str
    translated_file_name: Optional[str]
    translated_file_path: Optional[str]
    status: str
    duration: float
    error: Optional[str]

    class Config:
        from_attributes = True


@router.post("/file/history/create", response_model=FileTranslationHistoryResponse)
async def create_file_translation_history(
    task_id: str,
    current_user: User = Depends(get_current_user),
    credentials: dict = Depends(auth_middleware),
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
):
    """
    Insert file translation status into history
    """
    try:
        # Get user_id from credentials
        user_id = current_user.email

        # Get translation status from cache
        status_cache = FileTranslationStatusCache(redis_client)
        status = await status_cache.get_status(user_id, task_id)

        if not status:
            raise HTTPException(
                status_code=404,
                detail=f"Translation status not found for task_id: {task_id}",
            )

        # Create history dao
        history_dao = FileTranslationHistoryDao(db)

        # Insert into history
        history = await history_dao.insert(
            user_id=user_id,
            task_id=task_id,
            task_name=status.task_name,
            source_file_name=(
                os.path.basename(status.input_file_path)
                if status.input_file_path
                else ""
            ),
            source_file_path=status.input_file_path or "",
            translated_file_name=(
                os.path.basename(status.output_file_path)
                if status.output_file_path
                else None
            ),
            translated_file_path=status.output_file_path,
            status=status.status.value,
            duration=status.duration or 0.0,
            error=status.error,
        )

        return history

    except Exception as e:
        logger.error(f"Error inserting translation history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/file/history", response_model=List[FileTranslationHistoryResponse])
async def get_file_translation_history(
    current_user: User = Depends(get_current_user),
    credentials: dict = Depends(auth_middleware),
    db: Session = Depends(get_db),
):
    """
    Get all translation history for the user
    """
    try:
        # Get user_id from credentials
        user_id = current_user.email

        # Create history dao
        history_dao = FileTranslationHistoryDao(db)

        # Get all history for user
        histories = await history_dao.get_by_user_id(user_id)

        return histories

    except Exception as e:
        logger.error(f"Error getting translation history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
