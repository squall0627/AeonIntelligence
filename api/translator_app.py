from flask import request, jsonify, Flask

from core.ai_core.translation.language import Language
from core.ai_core.translation.translator import Translator

translator_app = Flask(__name__)

@translator_app.route("/")
def index():
    return "Hello, This is the translator app!"

@translator_app.route("/translate", methods=["POST"])
def translate():
    data = request.get_json()
    input_text = data["text"]
    source_language = data["source_language"]
    target_language = data["target_language"]
    keywords_map = data["keywords_map"] if "keywords_map" in data else {}

    translator = Translator(source_language, target_language, keywords_map)
    translated_text = translator.translate(input_text)

    return jsonify({"translated_text": translated_text})

@translator_app.route("/chinese_to_japanese", methods=["POST"])
def chinese_to_japanese():
    data = request.get_json()
    input_text = data["text"]
    keywords_map = data["keywords_map"] if "keywords_map" in data else {}

    translator = Translator(Language.CHINESE, Language.JAPANESE, keywords_map)
    translated_text = translator.translate(input_text)

    return jsonify({"translated_text": translated_text})

@translator_app.route("/japanese_to_chinese", methods=["POST"])
def japanese_to_chinese():
    data = request.get_json()
    input_text = data["text"]
    keywords_map = data["keywords_map"] if "keywords_map" in data else {}

    translator = Translator(Language.JAPANESE, Language.CHINESE, keywords_map)
    translated_text = translator.translate(input_text)

    return jsonify({"translated_text": translated_text})

if __name__ == "__main__":
    translator_app.run(host="0.0.0.0", port=5001, debug=True)