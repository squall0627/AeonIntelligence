import os
import tempfile

from flask import request, jsonify, Flask, send_from_directory, send_file
from werkzeug.utils import secure_filename

from core.ai_core.translation.file_translator.file_translator_builder import (
    FileTranslatorBuilder,
)
from core.ai_core.translation.language import Language
from core.ai_core.translation.text_translator import TextTranslator
from core.utils.log_handler import rotating_file_logger

from dotenv import load_dotenv

load_dotenv()

logger = rotating_file_logger("translator_app")
translator_app = Flask(__name__)

# Temp directory to save uploaded and translated files
UPLOAD_FOLDER = "translation/original"
TRANSLATED_FOLDER = "translation/translated"


@translator_app.route("/")
def index():
    return "Hello, This is the translator app!"


@translator_app.route("/translate", methods=["POST"])
def translate():
    logger.info("translate endpoint called")

    data = request.get_json()
    logger.info(f"Data: {data}")

    input_text = data["text"]
    source_language = data["source_language"]
    target_language = data["target_language"]
    keywords_map = data["keywords_map"] if "keywords_map" in data else {}

    translator = TextTranslator(source_language, target_language, keywords_map)
    translated_text = translator.translate(input_text)

    logger.info(f"Translated text: {translated_text}")

    return jsonify({"translated_text": translated_text})


@translator_app.route("/translate_file", methods=["POST"])
def translate_file():
    """
    API for translating files.
    Expected input:
    - A file upload.
    - Source and Target language codes as form data.
    """

    logger.info("translate_file endpoint called")

    # Check if the file is in the request
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    logger.info(f"File: {file.filename}")

    # Get language codes from the form data
    source_language = request.form.get("source_language")
    logger.info(f"Source language: {source_language}")
    target_language = request.form.get("target_language")
    logger.info(f"Target language: {target_language}")

    # Ensure the uploaded file has a safe and valid name
    filename = secure_filename(file.filename)

    # Save the uploaded file to a temporary system location
    temp_dir = os.getenv("TEMP_PATH", tempfile.gettempdir())
    input_dir = os.path.join(temp_dir, UPLOAD_FOLDER)
    os.makedirs(input_dir, exist_ok=True)
    input_file_path = os.path.join(input_dir, filename)
    file.save(input_file_path)
    logger.info(f"Uploaded file saved to: {input_file_path}")

    # Set up the output path for the translated file
    output_dir = os.path.join(temp_dir, TRANSLATED_FOLDER)
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Initialize the translator and perform the translation
        translator = FileTranslatorBuilder.build_file_translator(
            input_file_path, source_language, target_language
        )
        output_file_path = translator.translate(output_dir)
        logger.info(f"Translated file saved to: {output_file_path}")
    except Exception as e:
        return jsonify({"error": f"Translation failed: {str(e)}"}), 500

    # Return the translated file as a downloadable response
    return send_file(output_file_path, as_attachment=True)


@translator_app.route("/chinese_to_japanese", methods=["POST"])
def chinese_to_japanese():
    logger.info("chinese_to_japanese endpoint called")

    data = request.get_json()
    logger.info(f"Data: {data}")

    input_text = data["text"]
    keywords_map = data["keywords_map"] if "keywords_map" in data else {}

    translator = TextTranslator(Language.CHINESE, Language.JAPANESE, keywords_map)
    translated_text = translator.translate(input_text)

    logger.info(f"Translated text: {translated_text}")

    return jsonify({"translated_text": translated_text})


@translator_app.route("/japanese_to_chinese", methods=["POST"])
def japanese_to_chinese():
    logger.info("japanese_to_chinese endpoint called")

    data = request.get_json()
    logger.info(f"Data: {data}")

    input_text = data["text"]
    keywords_map = data["keywords_map"] if "keywords_map" in data else {}

    translator = TextTranslator(Language.JAPANESE, Language.CHINESE, keywords_map)
    translated_text = translator.translate(input_text)

    logger.info(f"Translated text: {translated_text}")

    return jsonify({"translated_text": translated_text})


if __name__ == "__main__":
    translator_app.run(host="0.0.0.0", port=5001, debug=True)
