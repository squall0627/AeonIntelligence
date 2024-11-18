import datetime

from langchain_core.prompts import PromptTemplate, BasePromptTemplate, ChatPromptTemplate, SystemMessagePromptTemplate, \
    MessagesPlaceholder, HumanMessagePromptTemplate
from pydantic import ConfigDict, create_model

DEFAULT_CHATBOT_NAME = "Aeon Intelligence"

class CustomPromptsDict(dict):
    def __init__(self, p_type, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._type = p_type

    def __setitem__(self, key, value):
        # Automatically convert the value into a tuple (my_type, value)
        super().__setitem__(key, (self._type, value))

def _define_custom_prompts() -> CustomPromptsDict:
    custom_prompts_inner: CustomPromptsDict = CustomPromptsDict(p_type=BasePromptTemplate)

    today_date = datetime.datetime.now().strftime("%B %d, %Y")

    # ---------------------------------------------------------------------------
    # Prompt for question rephrasing
    # ---------------------------------------------------------------------------
    system_message_template = (
        "Given a chat history and the latest user question "
        "which might reference context in the chat history, "
        "formulate a standalone question which can be understood "
        "without the chat history. Do NOT answer the question, "
        "just reformulate it if needed and otherwise return it as is. "
        "Do not output your reasoning, just the question."
    )

    template_answer = "User question: {question}\n Standalone question:"

    condense_question_prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(system_message_template),
            MessagesPlaceholder(variable_name="chat_history"),
            HumanMessagePromptTemplate.from_template(template_answer),
        ]
    )

    custom_prompts_inner["CONDENSE_QUESTION_PROMPT"] = condense_question_prompt


    # ---------------------------------------------------------------------------
    # Prompt for formatting documents
    # ---------------------------------------------------------------------------
    default_document_prompt = PromptTemplate.from_template(
        template="Filename: {original_file_name}\nSource: {index} \n {page_content}"
    )

    custom_prompts_inner["DEFAULT_DOCUMENT_PROMPT"] = default_document_prompt


    # ---------------------------------------------------------------------------
    # Prompt for RAG
    # ---------------------------------------------------------------------------
    system_message_template = f"Your name is {DEFAULT_CHATBOT_NAME}. You're a helpful assistant. Today's date is {today_date}. "

    system_message_template += (
        "- When answering use markdown. Use markdown code blocks for code snippets.\n"
        "- Answer in a concise and clear manner.\n"
        "- If no preferred language is provided, answer in the same language as the language used by the user.\n"
        "- You must use ONLY the provided context to answer the question. "
        "Do not use any prior knowledge or external information, even if you are certain of the answer.\n"
        "- If you cannot provide an answer using ONLY the context provided, do not attempt to answer from your own knowledge."
        "Instead, inform the user that the answer isn't available in the context and suggest using the available tools {tools}.\n"
        "- Do not apologize when providing an answer.\n"
        "- Don't cite the source id in the answer objects, but you can use the source to answer the question.\n\n"
    )

    context_template = (
        "\n"
        "- You have access to the following internal reasoning to provide an answer: {reasoning}\n"
        "- You have access to the following files to answer the user question (limited to first 20 files): {files}\n"
        "- You have access to the following context to answer the user question: {context}\n"
        "- Follow these user instruction when crafting the answer: {custom_instructions}\n"
        "- These user instructions shall take priority over any other previous instruction.\n"
        "- Remember: if you cannot provide an answer using ONLY the provided context and CITING the sources, "
        "inform the user that you don't have the answer and consider if any of the tools can help answer the question.\n"
        "- Explain your reasoning about the potential tool usage in the answer.\n"
        "- Only use binded tools to answer the question.\n"
    )

    template_answer = (
        "Original task: {question}\n"
        "Rephrased and contextualized task: {rephrased_task}\n"
    )

    rag_answer_prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(system_message_template),
            MessagesPlaceholder(variable_name="chat_history"),
            SystemMessagePromptTemplate.from_template(context_template),
            HumanMessagePromptTemplate.from_template(template_answer),
        ]
    )
    custom_prompts_inner["RAG_ANSWER_PROMPT"] = rag_answer_prompt


    # ---------------------------------------------------------------------------
    # Prompt to grade the relevance of an answer and decide whether to perform a web search
    # ---------------------------------------------------------------------------
    system_message_template = (
        "Given the following tasks you shall determine whether all tasks can be "
        "completed fully and in the best possible way using the provided context and chat history. "
        "You shall:\n"
        "- Consider each task separately,\n"
        "- Determine whether the context and chat history contain "
        "all the information necessary to complete the task.\n"
        "- If the context and chat history do not contain all the information necessary to complete the task, "
        "consider ONLY the list of tools below and select the tool most appropriate to complete the task.\n"
        "- If no tools are listed, return the tasks as is and no tool.\n"
        "- If no relevant tool can be selected, return the tasks as is and no tool.\n"
        "- Do not propose to use a tool if that tool is not listed among the available tools.\n"
    )

    context_template = "Context: {context}\n {activated_tools}\n"

    template_answer = "Tasks: {tasks}\n"

    tool_routing_prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(system_message_template),
            MessagesPlaceholder(variable_name="chat_history"),
            SystemMessagePromptTemplate.from_template(context_template),
            HumanMessagePromptTemplate.from_template(template_answer),
        ]
    )

    custom_prompts_inner["TOOL_ROUTING_PROMPT"] = tool_routing_prompt

    return custom_prompts_inner

_custom_prompts = _define_custom_prompts()
CustomPromptsModel = create_model(
    "CustomPromptsModel", **_custom_prompts, __config__=ConfigDict(extra="forbid")
)

custom_prompts = CustomPromptsModel()