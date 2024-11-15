from typing import no_type_check, Tuple, Any

from langchain_core.messages import AIMessageChunk
from langchain_core.prompts import format_document

from core.ai_core.llm.llm_config import LLMEndpointConfig
from core.ai_core.rag.entities.models import AiKnowledge, RawRAGResponse, ParsedRAGResponse, RAGResponseMetadata, \
    ChatLLMMetadata
from core.ai_core.rag.prompts import custom_prompts


def combine_documents(
        docs,
        document_prompt=custom_prompts.DEFAULT_DOCUMENT_PROMPT,
        document_separator="\n\n",
):
    # 各ドキュメントに対して、ソースを引用できるようにメタデータにインデックスを追加します。
    for doc, index in zip(docs, range(len(docs)), strict=False):
        doc.metadata["index"] = index
    doc_strings = [format_document(doc, document_prompt) for doc in docs]
    return document_separator.join(doc_strings)

def format_file_list(
        list_files_array: list[AiKnowledge], max_files: int = 20
) -> str:
    list_files = [file.file_name or file.url for file in list_files_array]
    files: list[str] = list(filter(lambda n: n is not None, list_files))
    files = files[:max_files]

    files_str = "\n".join(files) if list_files_array else "None"
    return files_str

@no_type_check
def parse_response(raw_response: RawRAGResponse, llm_endpoint_config: LLMEndpointConfig) -> ParsedRAGResponse:
    answers = []
    sources = raw_response["docs"] if "docs" in raw_response else []

    metadata = RAGResponseMetadata(
        sources=sources, metadata_model=ChatLLMMetadata(name=llm_endpoint_config.model)
    )

    if (
            llm_endpoint_config.supports_func_calling
            and "tool_calls" in raw_response["answer"]
            and raw_response["answer"].tool_calls
    ):
        all_citations = []
        all_followup_questions = []
        for tool_call in raw_response["answer"].tool_calls:
            if "args" in tool_call:
                args = tool_call["args"]
                if "citations" in args:
                    all_citations.extend(args["citations"])
                if "followup_questions" in args:
                    all_followup_questions.extend(args["followup_questions"])
                if "answer" in args:
                    answers.append(args["answer"])
        metadata.citations = all_citations
        metadata.followup_questions = all_followup_questions
    else:
        answers.append(raw_response["answer"].content)

    answer_str = "\n".join(answers)
    parsed_response = ParsedRAGResponse(answer=answer_str, metadata=metadata)
    return parsed_response

def get_answers_from_tool_calls(tool_calls):
    answers = []
    for tool_call in tool_calls:
        if tool_call.get("name") == "cited_answer" and "args" in tool_call:
            answers.append(tool_call["args"].get("answer", ""))
    return answers

@no_type_check
def parse_chunk_response(
        rolling_msg: AIMessageChunk,
        raw_chunk: AIMessageChunk,
        supports_func_calling: bool,
        previous_content: str = "",
) -> Tuple[AIMessageChunk, str, str]:

    rolling_msg += raw_chunk

    if not supports_func_calling or not rolling_msg.tool_calls:
        new_content = raw_chunk.content
        full_content = rolling_msg.content
        return rolling_msg, new_content, full_content

    current_answers = get_answers_from_tool_calls(rolling_msg.tool_calls)
    full_answer = "\n\n".join(current_answers)
    new_content = full_answer[len(previous_content) :]

    return rolling_msg, new_content, full_answer

def get_chunk_metadata(
        msg: AIMessageChunk, sources: list[Any] | None = None
) -> RAGResponseMetadata:
    metadata = {"sources": sources or []}

    if not msg.tool_calls:
        return RAGResponseMetadata(**metadata, metadata_model=None)

    all_citations = []
    all_followup_questions = []

    for tool_call in msg.tool_calls:
        if tool_call.get("name") == "cited_answer" and "args" in tool_call:
            args = tool_call["args"]
            all_citations.extend(args.get("citations", []))
            all_followup_questions.extend(args.get("followup_questions", []))

    metadata["citations"] = all_citations
    metadata["followup_questions"] = all_followup_questions[:3]  # Limit to 3

    return RAGResponseMetadata(**metadata, metadata_model=None)