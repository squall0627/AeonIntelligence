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
        # "- If no preferred language is provided, you MUST ONLY answer in the same language as the language used by the user.\n"
        "- you MUST ONLY answer in Japanese.\n"
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
        # "- If the context is in a different language than the {question}, you MUST translate the context into the same language as the {question}.\n"
        "- Follow these user instruction when crafting the answer: {custom_instructions}\n"
        "- These user instructions shall take priority over any other previous instruction.\n"
        "- Remember: if you cannot provide an answer using ONLY the provided context and CITING the sources, "
        "inform the user that you don't have the answer and consider if any of the tools can help answer the question.\n"
        "- Explain your reasoning about the potential tool usage in the answer.\n"
        "- Only use bound tools to answer the question.\n"
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


    # ---------------------------------------------------------------------------
    # Prompt to split the user input into multiple questions / instructions
    # ---------------------------------------------------------------------------
    system_message_template = (
        "Given a chat history and the user input, split and rephrase the input into instructions and tasks.\n"
        "- Instructions direct the system to behave in a certain way or to use specific tools: examples of instructions are "
        "'Can you reply in French?', 'Answer in French', 'You are an expert legal assistant', "
        "'You will behave as...', 'Use web search').\n"
        "- You shall collect and condense all the instructions into a single string.\n"
        "- The instructions shall be standalone and self-contained, so that they can be understood "
        "without the chat history. If no instructions are found, return an empty string.\n"
        "- Instructions to be understood may require considering the chat history.\n"
        "- Tasks are often questions, but they can also be summarization tasks, translation tasks, content generation tasks, etc.\n"
        "- Tasks to be understood may require considering the chat history.\n"
        "- If the user input contains different tasks, you shall split the input into multiple tasks.\n"
        "- Each split task shall be a standalone, self-contained task which can be understood "
        "without the chat history. You shall rephrase the tasks if needed.\n"
        "- If no explicit task is present, you shall infer the tasks from the user input and the chat history.\n"
        "- Do NOT try to solve the tasks or answer the questions, "
        "just reformulate them if needed and otherwise return them as is.\n"
        "- Remember, you shall NOT suggest or generate new tasks.\n"
        "- As an example, the user input 'What is Apple? Who is its CEO? When was it founded?' "
        "shall be split into the questions 'What is Apple?', 'Who is the CEO of Apple?' and 'When was Apple founded?'.\n"
        "- If no tasks are found, return the user input as is in the task.\n"
    )

    template_answer = "User input: {user_input}"

    split_prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(system_message_template),
            MessagesPlaceholder(variable_name="chat_history"),
            HumanMessagePromptTemplate.from_template(template_answer),
        ]
    )
    custom_prompts_inner["SPLIT_PROMPT"] = split_prompt


    # ---------------------------------------------------------------------------
    # Prompt to create a system prompt from user instructions
    # ---------------------------------------------------------------------------
    system_message_template = (
        "- Given the following user instruction, current system prompt, list of available tools "
        "and list of activated tools, update the prompt to include the instruction and decide which tools to activate.\n"
        "- The prompt shall only contain generic instructions which can be applied to any user task or question.\n"
        "- The prompt shall be concise and clear.\n"
        "- If the system prompt already contains the instruction, do not add it again.\n"
        "- If the system prompt contradicts the user instruction, remove the contradictory "
        "statement or statements in the system prompt.\n"
        "- You shall return separately the updated system prompt and the reasoning that led to the update.\n"
        "- If the system prompt refers to a tool, you shall add the tool to the list of activated tools.\n"
        "- If no tool activation is needed, return empty lists.\n"
        "- You shall also return the reasoning that led to the tool activation.\n"
        "- Current system prompt: {system_prompt}\n"
        "- List of available tools: {available_tools}\n"
        "- List of activated tools: {activated_tools}\n\n"
    )

    template_answer = "User instructions: {instruction}\n"

    update_prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(system_message_template),
            HumanMessagePromptTemplate.from_template(template_answer),
        ]
    )
    custom_prompts_inner["UPDATE_PROMPT"] = update_prompt

    return custom_prompts_inner

_custom_prompts = _define_custom_prompts()
CustomPromptsModel = create_model(
    "CustomPromptsModel", **_custom_prompts, __config__=ConfigDict(extra="forbid")
)

custom_prompts = CustomPromptsModel()