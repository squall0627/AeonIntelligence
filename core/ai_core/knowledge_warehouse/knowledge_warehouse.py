import asyncio
import logging
import os
import shutil

from pathlib import Path
from pprint import PrettyPrinter
from typing import Any, AsyncGenerator, Callable, Dict, Self, Type, Union
from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree
from uuid import UUID, uuid4
from dataclasses import dataclass

from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage

from core.ai_core.embedder.embedder_base import EmbedderBase
from core.ai_core.files import AIFile
from core.ai_core.files.file import load_aifile
from core.ai_core.knowledge_warehouse.serialization import KWSerialized
from core.ai_core.llm.llm_endpoint import LLMEndpoint, LLMInfo, default_rag_llm
from core.ai_core.processor.processor_registry import get_processor_class
from core.ai_core.rag.config.ai_rag_config import RetrievalConfig
from core.ai_core.rag.ai_rag_langgraph import AiQARAGLangGraph
from core.ai_core.rag.entities.chat import ChatHistoryInfo, ChatHistory
from core.ai_core.rag.entities.models import (
    SearchResult,
    AIKnowledge,
    ParsedRAGChunkResponse,
    ParsedRAGResponse,
)
from core.ai_core.storage.storage_base import StorageBase, StorageInfo
from core.ai_core.storage.storage_builder import StorageBuilder
from core.ai_core.embedder.embedder_builder import EmbedderBuilder
from core.ai_core.vectordb.vectordb_base import VectordbBase
from core.ai_core.vectordb.vectordb_builder import VectordbBuilder

logger = logging.getLogger("ai_core")


async def process_file(
    file: AIFile, **processor_kwargs: dict[str, Any]
) -> list[Document]:
    """
    ストレージ内のファイルを処理します。
    この関数は AIFile を受け取り、Langchain ドキュメントのリストを返します。
    引数:
    - file (AIFile): 処理するファイルを含むストレージ。
    - processor_kwargs (dict[str, Any]): プロセッサへの追加の引数。

    戻り値:
    - list[Document]: Langchain ドキュメント形式で処理されたドキュメントのリスト。

    例外:
    - ValueError: ファイルを処理できず、かつ skip_file_error が False の場合。
    - Exception: 特定の種類のファイルのプロセッサが見つからず、かつ skip_file_error が False の場合。
    """

    knowledge = []

    try:
        if file.file_extension:
            processor_cls = get_processor_class(file.file_extension)
            logger.debug(f"processing {file} using class {processor_cls.__name__}")
            processor = processor_cls(**processor_kwargs)
            docs = await processor.process_file(file)
            knowledge.extend(docs)
        else:
            logger.error(f"can't find processor for {file}")
            raise ValueError(f"can't parse {file}. can't find file extension")
    except KeyError as e:
        raise Exception(f"Can't parse {file}. No available processor") from e

    return knowledge


@dataclass
class KnowledgeWarehouseInfo:
    kw_id: UUID
    kw_name: str
    chats_info: ChatHistoryInfo
    llm_info: LLMInfo
    files_info: StorageInfo | None = None

    def to_tree(self):
        tree = Tree("📊 Knowledge Warehouse Information")
        tree.add(f"🆔 ID: [bold cyan]{self.kw_id}[/bold cyan]")
        tree.add(
            f"🧠 Knowledge Warehouse Name: [bold green]{self.kw_name}[/bold green]"
        )

        if self.files_info:
            files_tree = tree.add("📁 Files")
            self.files_info.add_to_tree(files_tree)

        chats_tree = tree.add("💬 Chats")
        self.chats_info.add_to_tree(chats_tree)

        llm_tree = tree.add("🤖 LLM")
        self.llm_info.add_to_tree(llm_tree)
        return tree


class KnowledgeWarehouse:
    """
    KnowledgeWarehouse を表すクラス。
    このクラスは情報を取得したい知識のコレクションとしての KnowledgeWarehouse を作成するために使用されます。機能は以下のとおりです：
    - 任意のストレージ（ローカル、S3 など）にファイルを保存。
    - ストレージ内のファイルを処理し、さまざまな形式でテキストとメタデータを抽出。
    - 処理されたファイルを任意の vector store（FAISS、Pinecone など）に保存（デフォルトは FAISS）。
    - 処理されたファイルのインデックスを作成。
    - *Aeon Intelligence* ワークフローを使用して、RAG(retrieval augmented generation) 検索を行う。

    KnowledgeWarehouse は以下を行うことができます：
    - vector store 内での情報検索。
    - KnowledgeWarehouse 内の知識に関する質問に答える。
    - 質問への回答をストリーム形式で提供。

    プロパティ:
    - name (str): KnowledgeWarehouse の名前。
    - kw_id (UUID): KnowledgeWarehouse の一意の識別子。
    - storage (StorageBase): ファイルを保存するために使用するストレージ。
    - llm (LLMEndpoint): 回答を生成するために使用する言語モデル。
    - vector_db (VectordbBase): 処理されたファイルを保存する vector store。
    - embedder (EmbedderBase): 処理されたファイルのインデックスを作成するために使用する Embeddings。
    """

    def __init__(
        self,
        *,
        name: str,
        llm: LLMEndpoint,
        kw_id: UUID | None = None,
        vector_db: VectordbBase | None = None,
        embedder: EmbedderBase | None = None,
        storage: StorageBase | None = None,
        kw_path: str | Path | None = None,
    ):
        self.kw_id = kw_id
        self.name = name
        self.storage = storage

        # Chat 履歴
        self._chats = self._init_chats()
        self.default_chat = list(self._chats.values())[0]

        # RAG dependencies:
        self.llm = llm
        self.vector_db = vector_db
        self.embedder = embedder

        # Path to the folder where the KW is saved
        self.kw_path = kw_path

    def __repr__(self) -> str:
        pp = PrettyPrinter(width=80, depth=None, compact=False, sort_dicts=False)
        return pp.pformat(self.info())

    def print_info(self):
        console = Console()
        tree = self.info().to_tree()
        panel = Panel(
            tree, title="Knowledge Warehouse Info", expand=False, border_style="bold"
        )
        console.print(panel)

    @classmethod
    def load(cls, folder_path: str | Path) -> Self:
        """
        フォルダパスから KnowledgeWarehouse を読み込む。
        引数:
        - folder_path (str | Path): KnowledgeWarehouse を含むフォルダへのパス。

        戻り値:
        - KnowledgeWarehouse: フォルダパスから読み込まれた KnowledgeWarehouse。

        例:
        ```python
        kw_loaded = KnowledgeWarehouse.load("path/to/KnowledgeWarehouse")
        kw_loaded.print_info()
        ```
        """
        if isinstance(folder_path, str):
            folder_path = Path(folder_path)
        if not folder_path.exists():
            raise ValueError(f"path {folder_path} doesn't exist")

        # Load KWSerialized
        with open(os.path.join(folder_path, "config.json"), "r") as f:
            kw_serialized = KWSerialized.model_validate_json(f.read())

        # Loading storage
        storage = StorageBuilder.load_storage(kw_serialized.storage_config)

        # Load Embedder
        embedder = EmbedderBuilder.load_embedder(kw_serialized.embedding_config)

        # Load vector db
        vector_db = VectordbBuilder.load_vectordb(
            kw_serialized.vectordb_config, embedder.embedder
        )

        return cls(
            kw_id=kw_serialized.kw_id,
            name=kw_serialized.kw_name,
            embedder=embedder,
            llm=LLMEndpoint.from_config(kw_serialized.llm_config),
            storage=storage,
            vector_db=vector_db,
            kw_path=folder_path,
        )

    async def save(self, folder_path: str | Path):
        """
        Knowledge Warehouse をフォルダパスに保存します。

        引数:
        - folder_path (str | Path): Knowledge Warehouse を保存するフォルダのパス。

        戻り値:
        - str: Knowledge Warehouse が保存されたフォルダのパス。

        例:
        ```python
        await kw.save("path/to/KnowledgeWarehouse")
        ```
        """
        if isinstance(folder_path, str):
            folder_path = Path(folder_path)

        kw_path = os.path.join(folder_path, f"kw_{self.kw_id}")
        os.makedirs(kw_path, exist_ok=True)

        self.kw_path = kw_path

        # Save serialized vector db
        vectordb_config = await self.vector_db.save(kw_path)

        # Save serialized embedder
        embedder_config = self.embedder.save()

        # Save serialized storage
        storage_config = StorageBuilder.save_storage(self.storage)

        kw_serialized = KWSerialized(
            kw_id=self.kw_id,
            kw_name=self.name,
            chat_history=self.chat_history.get_chat_history(),
            llm_config=self.llm.get_config(),
            vectordb_config=vectordb_config,
            embedding_config=embedder_config,
            storage_config=storage_config,
        )

        with open(os.path.join(kw_path, "config.json"), "w") as f:
            f.write(kw_serialized.model_dump_json())
        return kw_path

    async def delete(self) -> None:
        """Delete the entire knowledge warehouse including all files and vectors."""
        try:
            # Delete the storage directory if it exists
            if self.storage and self.storage.get_directory_path():
                storage_root = self.storage.get_directory_path()
                kw_storage_file_path = os.path.join(storage_root, str(self.kw_id))
                if os.path.exists(kw_storage_file_path):
                    shutil.rmtree(kw_storage_file_path)

            # Delete vector store if it exists
            self.vector_db.vector_db.delete(self.vector_db.get_all_ids())

            # Delete all files under self.kw_path
            if os.path.exists(self.kw_path):
                shutil.rmtree(self.kw_path)

        except Exception as e:
            logger.error(f"Error deleting knowledge warehouse: {self.name} {str(e)}")
            raise e

    def info(self) -> KnowledgeWarehouseInfo:
        # TODO: embedding
        chats_info = ChatHistoryInfo(
            nb_chats=len(self._chats),
            current_default_chat=self.default_chat.id,
            current_chat_history_length=len(self.default_chat),
        )

        return KnowledgeWarehouseInfo(
            kw_id=self.kw_id,
            kw_name=self.name,
            files_info=self.storage.info() if self.storage else None,
            chats_info=chats_info,
            llm_info=self.llm.info(),
        )

    @property
    def chat_history(self) -> ChatHistory:
        return self.default_chat

    def get_chat_history(self, chat_id: UUID):
        return self._chats[chat_id]

    def _init_chats(self) -> Dict[UUID, ChatHistory]:
        chat_id = uuid4()
        default_chat = ChatHistory(chat_id=chat_id, kw_id=self.kw_id)
        return {chat_id: default_chat}

    @classmethod
    async def afrom_files(
        cls,
        *,
        name: str,
        file_paths: list[str | Path],
        vector_db: VectordbBase | None = None,
        storage: StorageBase = StorageBuilder.build_default_storage(None, None),
        llm: LLMEndpoint | None = None,
        embedder: EmbedderBase | None = None,
        skip_file_error: bool = False,
        processor_kwargs: dict[str, Any] | None = None,
    ):
        """
        ファイルパスのリストから KnowledgeWarehouse を作成する。
        引数:
        - name (str): KnowledgeWarehouse の名前。
        - file_paths (list[str | Path]): KnowledgeWarehouse に追加するファイルパスのリスト。
        - vector_db (VectordbBase | None): 処理されたファイルを保存するために使用する VectorStore。
        - storage (StorageBase): ファイルを保存するために使用するストレージ。
        - llm (LLMEndpoint | None): 回答を生成するために使用する言語モデル。
        - embedder (Embeddings | None): 処理されたファイルのインデックスを作成するために使用する Embeddings。
        - skip_file_error (bool): 処理できないファイルをスキップするかどうか。
        - processor_kwargs (dict[str, Any] | None): プロセッサへの追加の引数。

        戻り値:
        - KnowledgeWarehouse: ファイルパスから作成された KnowledgeWarehouse。

        例:
        ```python
        kw = await KnowledgeWarehouse.afrom_files(name="My Knowledge Warehouse", file_paths=["file1.pdf", "file2.pdf"])
        kw.print_info()
        ```
        """
        if llm is None:
            llm = default_rag_llm()

        if embedder is None:
            embedder = EmbedderBuilder.build_default_embedder()

        kw_id = uuid4()

        # Add files to storage and vector db
        vector_db = await cls._add_file_to_storage_and_vectordb(
            kw_id=kw_id,
            file_paths=file_paths,
            storage=storage,
            embedder=embedder,
            skip_file_error=skip_file_error,
            processor_kwargs=processor_kwargs,
        )

        return cls(
            kw_id=kw_id,
            name=name,
            storage=storage,
            llm=llm,
            embedder=embedder,
            vector_db=vector_db,
        )

    @classmethod
    def from_files(
        cls,
        *,
        name: str,
        file_paths: list[str | Path],
        vector_db: VectordbBase | None = None,
        storage: StorageBase = StorageBuilder.build_default_storage(None, None),
        llm: LLMEndpoint | None = None,
        embedder: EmbedderBase | None = None,
        skip_file_error: bool = False,
        processor_kwargs: dict[str, Any] | None = None,
    ) -> Self:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            cls.afrom_files(
                name=name,
                file_paths=file_paths,
                vector_db=vector_db,
                storage=storage,
                llm=llm,
                embedder=embedder,
                skip_file_error=skip_file_error,
                processor_kwargs=processor_kwargs,
            )
        )

    async def asearch(
        self,
        query: str | Document,
        n_results: int = 5,
        search_filter: Callable | Dict[str, Any] | None = None,
        fetch_n_neighbors: int = 20,
    ) -> list[SearchResult]:
        """
        クエリに基づいて KnowledgeWarehouse 内の関連ドキュメントを検索する。
        引数:
        - query (str | Document): 検索するクエリ。
        - n_results (int): 返す結果の数。
        - search_filter (Callable | Dict[str, Any] | None): 検索に適用するフィルタ。
        - fetch_n_neighbors (int): 取得する近傍の数。

        戻り値:
        - list[SearchResult]: 取得したチャンクのリスト。

        例:
        ```python
        kw = KnowledgeWarehouse.from_files(name="My Knowledge Warehouse", file_paths=["file1.pdf", "file2.pdf"])
        results = await kw.asearch("What is your name?")
        for result in results:
            print(result.chunk.page_content)
        ```
        """
        if not self.vector_db:
            raise ValueError("No vector db configured for this Knowledge Warehouse")

        result = await self.vector_db.vector_db.asimilarity_search_with_score(
            query, k=n_results, filter=search_filter, fetch_k=fetch_n_neighbors
        )

        return [SearchResult(chunk=d, distance=s) for d, s in result]

    async def ask_streaming(
        self,
        question: str,
        retrieval_config: RetrievalConfig | None = None,
        rag_pipeline: Type[Union[AiQARAGLangGraph]] | None = None,
        list_files: list[AIKnowledge] | None = None,
        chat_history: ChatHistory | None = None,
    ) -> AsyncGenerator[ParsedRAGChunkResponse, ParsedRAGChunkResponse]:
        """
        KnowledgeWarehouse に質問をして、ストリーム形式で生成された回答を取得する。
        引数:
        - question (str): 質問内容。
        - retrieval_config (RetrievalConfig | None): 検索設定（詳細は RetrievalConfig のドキュメントを参照）。
        - rag_pipeline (Type[Union[AiQARAGLangGraph]] | None): 使用する RAG パイプライン。
        - list_files (list[AiKnowledge] | None): RAG パイプラインに含めるファイルのリスト。
        - chat_history (ChatHistory | None): 使用するチャット履歴。

        戻り値:
        - AsyncGenerator[ParsedRAGChunkResponse, ParsedRAGChunkResponse]: ストリーム形式で生成された回答。

        例:
        ```python
        kw = KnowledgeWarehouse.from_files(name="My Knowledge Warehouse", file_paths=["file1.pdf", "file2.pdf"])
        async for chunk in kw.ask_streaming("What is your name?"):
            print(chunk.answer)
        ```
        """
        llm = self.llm

        # 別の LLM モデルを渡した場合、KnowledgeWarehouse のモデルが上書きされます。
        if retrieval_config:
            if retrieval_config.llm_config != self.llm.get_config():
                llm = LLMEndpoint.from_config(config=retrieval_config.llm_config)
        else:
            retrieval_config = RetrievalConfig(llm_config=self.llm.get_config())

        if rag_pipeline is None:
            rag_pipeline = AiQARAGLangGraph

        rag_instance = rag_pipeline(
            retrieval_config=retrieval_config,
            llm=llm,
            vector_store=self.vector_db.vector_db,
        )

        chat_history = self.default_chat if chat_history is None else chat_history
        list_files = [] if list_files is None else list_files

        full_answer = ""

        async for response in rag_instance.answer_astream(
            question=question, history=chat_history, list_files=list_files
        ):
            # Format output
            if not response.last_chunk:
                yield response
            full_answer += response.answer

        chat_history.append(HumanMessage(content=question))
        chat_history.append(AIMessage(content=full_answer))
        yield response

    async def aask_streaming(
        self,
        question: str,
        retrieval_config: RetrievalConfig | None = None,
        rag_pipeline: Type[Union[AiQARAGLangGraph]] | None = None,
        list_files: list[AIKnowledge] | None = None,
        chat_history: ChatHistory | None = None,
    ) -> ParsedRAGResponse:
        """
        ask_streamingの同期化バージョン.
        引数:
        - question (str): 質問内容。
        - retrieval_config (RetrievalConfig | None): 検索設定（詳細は RetrievalConfig のドキュメントを参照）。
        - rag_pipeline (Type[Union[AiQARAGLangGraph]] | None): 使用する RAG パイプライン。
        - list_files (list[AiKnowledge] | None): RAG パイプラインに含めるファイルのリスト。
        - chat_history (ChatHistory | None): 使用するチャット履歴。

        戻り値:
        - ParsedRAGResponse: 生成された回答。
        """
        full_answer = ""
        metadata = None

        async for response in self.ask_streaming(
            question=question,
            retrieval_config=retrieval_config,
            rag_pipeline=rag_pipeline,
            list_files=list_files,
            chat_history=chat_history,
        ):
            full_answer += response.answer
            if response.last_chunk:
                metadata = response.metadata

        return ParsedRAGResponse(answer=full_answer, metadata=metadata)

    def ask(
        self,
        question: str,
        retrieval_config: RetrievalConfig | None = None,
        rag_pipeline: Type[Union[AiQARAGLangGraph]] | None = None,
        list_files: list[AIKnowledge] | None = None,
        chat_history: ChatHistory | None = None,
    ) -> ParsedRAGResponse:
        """
        ask_streamingの完全同期化バージョン.
        引数:
        - question (str): 質問内容。
        - retrieval_config (RetrievalConfig | None): 検索設定（詳細は RetrievalConfig のドキュメントを参照）。
        - rag_pipeline (Type[Union[AiQARAGLangGraph]] | None): 使用する RAG パイプライン。
        - list_files (list[AiKnowledge] | None): RAG パイプラインに含めるファイルのリスト。
        - chat_history (ChatHistory | None): 使用するチャット履歴。

        戻り値:
        - ParsedRAGResponse: 生成された回答。
        """
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            self.aask_streaming(
                question=question,
                retrieval_config=retrieval_config,
                rag_pipeline=rag_pipeline,
                list_files=list_files,
                chat_history=chat_history,
            )
        )

    @classmethod
    async def _add_file_to_storage_and_vectordb(
        cls,
        kw_id: UUID,
        file_paths: list[str | Path],
        storage: StorageBase,
        vector_db: VectordbBase | None = None,
        embedder: EmbedderBase | None = None,
        skip_file_error: bool = False,
        processor_kwargs: dict[str, Any] | None = None,
    ) -> VectordbBase | None:

        processor_kwargs = processor_kwargs or {}

        for path in file_paths:
            file = await load_aifile(kw_id, path)
            await storage.upload_file(file)

            logger.debug(f"uploaded {file} to {storage}")

            try:
                # Parse files
                docs = await process_file(
                    file=file,
                    **processor_kwargs,
                )
            except Exception as e:
                if skip_file_error:
                    logger.warning(f"error processing {file}: {e}")
                    continue
                else:
                    raise e

            # Building KnowledgeWarehouse's vectordb
            if vector_db is None:
                vector_db = await VectordbBuilder.build_default_vectordb(
                    docs, embedder.embedder
                )
                ids = vector_db.get_all_ids()
            else:
                ids = await vector_db.vector_db.aadd_documents(docs)

            file.vectordb_ids = ids

            logger.debug(f"added {len(docs)} chunks to vectordb")

        return vector_db

    async def aadd_files(
        self,
        file_paths: list[str | Path],
        skip_file_error: bool = False,
        processor_kwargs: dict[str, Any] | None = None,
    ) -> None:
        await self._add_file_to_storage_and_vectordb(
            kw_id=self.kw_id,
            file_paths=file_paths,
            storage=self.storage,
            vector_db=self.vector_db,
            embedder=self.embedder,
            skip_file_error=skip_file_error,
            processor_kwargs=processor_kwargs,
        )

    async def delete_file(self, file: AIFile) -> None:
        # Remove file from storage
        await self.storage.remove_file(file.file_id)
        logger.debug(
            f"removed file {file.original_filename} from {self.name}'s storage"
        )

        # Remove file from vector db
        self.vector_db.vector_db.delete(file.vectordb_ids)
        logger.debug(
            f"removed file {file.original_filename} from {self.name}'s vector db"
        )
