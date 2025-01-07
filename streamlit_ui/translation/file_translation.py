import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from time import sleep

import streamlit as st
import asyncio

from werkzeug.utils import secure_filename

from core.ai_core.translation.file_translator.file_translator_builder import (
    FileTranslatorBuilder,
)
from core.ai_core.translation.language import Language
from core.utils.log_handler import rotating_file_logger

logger = rotating_file_logger("translator_app")

# Temp directory to save uploaded and translated files
UPLOAD_FOLDER = "translation/original"
TRANSLATED_FOLDER = "translation/translated"


def all_task_done():
    return len(st.session_state.futures) == 0 or (
        len(st.session_state.futures) > 0
        and all(future.done() for future in st.session_state.futures.values())
    )


def refresh_status():
    for file_name, future in st.session_state.futures.items():
        if future.done():
            try:
                output_file_path, duration = future.result()
                st.success(
                    f"Translation completed in {duration} seconds for {file_name}."
                )
                st.markdown(f"[Download Translated File]({output_file_path})")
            except Exception as e:
                st.markdown(f"Translation failed for {file_name}.")
                logger.error({"error": f"Translation failed: {str(e)}"})

    if all_task_done():
        st.success("All translations completed.")
        st.session_state.futures = {}

    st.rerun()  # Refresh the page to get the latest translation status


def render_file_translation_page():
    # Initialize session_state
    if "futures" not in st.session_state:
        st.session_state.futures = {}

    if not all_task_done():
        sleep(1)
        refresh_status()

    st.title("File Translation")

    # File upload section
    uploaded_files = st.file_uploader(
        "Upload files for translation",
        accept_multiple_files=True,
        disabled=not all_task_done(),
    )

    # Language selection
    source_language = st.selectbox(
        "Select source language",
        [Language.ENGLISH, Language.CHINESE],
        disabled=not all_task_done(),
    )
    target_language = st.selectbox(
        "Select target language",
        [Language.JAPANESE, Language.ENGLISH],
        disabled=not all_task_done(),
    )

    # Translate button
    if st.button("Translate", disabled=not all_task_done()):
        if uploaded_files:
            # Start the translation process
            for uploaded_file in uploaded_files:
                # Ensure the uploaded file has a safe and valid name
                filename = secure_filename(uploaded_file.name)

                # Save the uploaded file to a temporary system location
                temp_dir = os.getenv("TEMP_PATH", tempfile.gettempdir())
                input_dir = os.path.join(temp_dir, UPLOAD_FOLDER)
                os.makedirs(input_dir, exist_ok=True)
                input_file_path = os.path.join(input_dir, filename)
                with open(input_file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                logger.info(f"Uploaded file saved to: {input_file_path}")

                # Set up the output path for the translated file
                output_dir = os.path.join(temp_dir, TRANSLATED_FOLDER)
                os.makedirs(output_dir, exist_ok=True)

                try:
                    # Initialize the translator and perform the translation
                    file_translator = FileTranslatorBuilder.build_file_translator(
                        input_file_path,
                        source_language,
                        target_language,
                        run_parallely=True,
                    )
                    # Schedule the coroutine as a task and store the Future
                    with ThreadPoolExecutor(max_workers=8) as executor:
                        st.session_state.futures[filename] = executor.submit(
                            file_translator.translate, output_dir
                        )

                    # Display a status bar
                    with st.spinner("Translating..."):
                        # Status bar at the bottom
                        st.progress(file_translator.status.progress)
                except Exception as e:
                    logger.error(
                        {"error": f"Translation failed: file name: {filename} {str(e)}"}
                    )
                    st.error(f"Translation failed for {filename}.")
                    continue

    # Refresh button
    if st.button("Refresh", disabled=all_task_done()):
        # Check and refresh the status of all tasks
        refresh_status()
