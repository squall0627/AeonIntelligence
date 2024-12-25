import datetime

from langchain_core.prompts import (
    BasePromptTemplate,
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from pydantic import ConfigDict, create_model


class TranslationPromptsDict(dict):
    def __init__(self, p_type, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._type = p_type

    def __setitem__(self, key, value):
        # Automatically convert the value into a tuple (my_type, value)
        super().__setitem__(key, (self._type, value))


def _define_translation_prompts() -> TranslationPromptsDict:
    translation_prompts_inner: TranslationPromptsDict = TranslationPromptsDict(
        p_type=BasePromptTemplate
    )

    today_date = datetime.datetime.now().strftime("%B %d, %Y")

    # ---------------------------------------------------------------------------
    # Prompt for translation
    # ---------------------------------------------------------------------------
    system_message_template = (
        "You are a highly skilled professional translator. \n"
        "You are a native speaker of English, Japanese and Chinese. \n"
        "Translate the given text accurately, taking into account the context and specific instructions provided. \n"
        "Steps may include hints enclosed in square brackets [] with the key and value separated by a colon:. \n"
        "When translating, You MUST strictly adhering to the rules below: \n"
        "1.If no additional instructions or context are provided, use your expertise to consider what the most appropriate context is and provide a natural translation that aligns with that context. \n"
        "2.When translating, strive to faithfully reflect the meaning and tone of the original text, pay attention to cultural nuances and differences in language usage, and ensure that the translation is grammatically correct and easy to read. \n"
        "3.You MUST always translate the specified terms from the provided Keywords Map into the target language while preserving their original context and nuance. \n"
        " Input Example:\n"
        '　 ・Keywords Map: {{"订单": "注文", "捡货": "ピッキング", "订单中心": "注文センター"}}\n'
        "　 ・Target Language: Japanese\n"
        " Output Example:\n"
        '　 ・"订单" → 注文\n'
        '　 ・"捡货" → ピッキング\n'
        '　 ・"订单中心" → 注文センター\n'
        "4.Do not translate URLs or their parameters： \n"
        "　・A URL is any string starting with http://, https://, or www., including query parameters (e.g., parts after ? and &). \n"
        "　・Example: https://example.com/path?param=value&key=123. The entire URL MUST remain unchanged. \n"
        " Input Example:\n"
        "　 ・请访问https://example.com/page?lang=zh-CN&token=abc123\n"
        "　 ・请不要点击http://www.figma.com/design/PnRr8GS7yRPrUQJ3thvkij/%E3%80%90V1.5%E3%80%91PM0001_%E3%82%AF%E3%83%BC%E3%83%9D%E3%83%B3%E4%B8%80%E8%A6%A7?node-id=4695-4202&node-type=frame&t=dUI7yNgTJUvhiRD5-0\n"
        " Output Example:\n"
        "　 ・https://example.com/page?lang=zh-CN&token=abc123をアクセスしてください\n"
        "　 ・http://www.figma.com/design/PnRr8GS7yRPrUQJ3thvkij/%E3%80%90V1.5%E3%80%91PM0001_%E3%82%AF%E3%83%BC%E3%83%9D%E3%83%B3%E4%B8%80%E8%A6%A7?node-id=4695-4202&node-type=frame&t=dUI7yNgTJUvhiRD5-0をクリックしないでください\n"
        # "5.DO NOT need to output your reasoning process, ONLY output your Final Translation. \n"
        "5.Provide the answer ONLY. DO NOT explain. \n"
        "6.If no text for translation is provided, DO NOT output anything. \n"
        "Take a deep breath, calm down, and start translating.\n\n"
    )

    keywords_map = "Keywords Map: {keywords_map}\n\n"
    instruction = "Instruction: {instruction}\n"
    input_text = "Input text: {input_text}\n"

    simple_translate = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(system_message_template),
            HumanMessagePromptTemplate.from_template(keywords_map),
            HumanMessagePromptTemplate.from_template(instruction),
            HumanMessagePromptTemplate.from_template(input_text),
        ]
    )

    translation_prompts_inner["SIMPLE_TRANSLATE_PROMPT"] = simple_translate

    return translation_prompts_inner


_translation_prompts = _define_translation_prompts()
TranslationPromptsModel = create_model(
    "TranslationPromptsModel",
    **_translation_prompts,
    __config__=ConfigDict(extra="forbid")
)

translation_prompts = TranslationPromptsModel()
