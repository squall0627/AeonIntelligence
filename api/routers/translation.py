import os
import tempfile

import stopwatch
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from werkzeug.utils import secure_filename

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
    source_language: Language
    target_language: Language
    keywords_map: Optional[dict] = None


class TranslationResponse(BaseModel):
    translated_text: str
    duration: Optional[float] = None


# Store translation tasks status
translation_tasks: dict[str, FileTranslationStatus] = {}

# Temp directory to save uploaded and translated files
UPLOAD_FOLDER = "translation/original"
TRANSLATED_FOLDER = "translation/translated"


@router.post("/text", response_model=TranslationResponse)
async def translate_text(
    params: TextTranslationRequest,
    credentials: dict = Depends(auth_middleware),
):
    logger.debug("credentials: " + str(credentials))
    sw = stopwatch.Stopwatch()
    sw.start()
    logger.info("translate text endpoint called")
    try:
        input_text = params.text
        source_language = params.source_language
        target_language = params.target_language
        keywords_map = params.keywords_map if params.keywords_map else {}

        translator = TextTranslator(source_language, target_language, keywords_map)
        translated_text = translator.translate(input_text)

        logger.info(f"Translated text: {translated_text}")

        sw.stop()
        return TranslationResponse(
            translated_text=translated_text,
            duration=sw.duration,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/file")
async def translate_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    source_language: Language = Language.ENGLISH,
    target_language: Language = Language.JAPANESE,
    keywords_map: dict | None = None,
    credentials: dict = Depends(auth_middleware),
    **kwargs,
):
    logger.debug("credentials: " + str(credentials))
    logger.info("translate file endpoint called")
    try:
        # Create unique task ID
        task_id = f"{datetime.now().timestamp()}_{file.filename}"

        # Ensure the uploaded file has a safe and valid name
        filename = secure_filename(file.filename)

        # Save the uploaded file to a temporary system location
        temp_dir = os.getenv("TEMP_PATH", tempfile.gettempdir())
        input_dir = os.path.join(temp_dir, UPLOAD_FOLDER)
        os.makedirs(input_dir, exist_ok=True)
        input_file_path = os.path.join(input_dir, filename)
        with open(input_file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        logger.info(f"Uploaded file saved to: {input_file_path}")

        # Add translation task to background tasks
        background_tasks.add_task(
            process_file_translation,
            task_id,
            input_file_path,
            source_language,
            target_language,
            keywords_map,
            **kwargs,
        )

        return {"task_id": task_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{task_id}", response_model=FileTranslationStatus)
async def get_translation_status(
    task_id: str, credentials: dict = Depends(auth_middleware)
):
    logger.debug("credentials: " + str(credentials))
    logger.info("get translation status endpoint called")
    if task_id not in translation_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return translation_tasks[task_id]


@router.get("/download/{task_id}")
async def download_translated_file(
    task_id: str, credentials: dict = Depends(auth_middleware)
):
    logger.debug("credentials: " + str(credentials))
    logger.info("download translated file endpoint called")
    if task_id not in translation_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = translation_tasks[task_id]
    if task.status != Status.COMPLETED:
        raise HTTPException(status_code=400, detail="Translation not completed")

    if not task.output_file_path or not os.path.exists(task.output_file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        task.output_file_path, filename=os.path.basename(task.output_file_path)
    )


async def process_file_translation(
    task_id: str,
    file_path: str,
    source_language: Language,
    target_language: Language,
    keywords_map,
    **kwargs,
):
    # Initialize translation status
    status = FileTranslationStatus(
        task_id=task_id, status=Status.PROCESSING, progress=0
    )

    try:
        # Initialize translation task
        translation_tasks[task_id] = status

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
        status = await file_translator.atranslate(output_dir)

    except Exception as e:
        # Update status to error
        status.status = Status.ERROR
        status.error = str(e)

    finally:
        # Cleanup temporary file
        if os.path.exists(file_path):
            os.remove(file_path)
