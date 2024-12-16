from typing import Any, List, Generator, Tuple
from dataclasses import dataclass
from uuid import UUID, uuid4

from pydantic import BaseModel
from datetime import datetime

from langchain_core.messages import AIMessage, HumanMessage, BaseMessage
from rich.tree import Tree


class ChatMessage(BaseModel):
    chat_id: UUID
    message_id: UUID
    kw_id: UUID | None
    msg: BaseMessage
    message_time: datetime
    metadata: dict[str, Any]


class ChatHistory:
    """
    ChatHistory はチャットの会話履歴を記録するクラスです。
    履歴内の各メッセージは ChatMessage クラスのインスタンスとして表され、チャット履歴はこれらの ChatMessage オブジェクトのリストとして内部的に保存されます。
    このクラスは、チャット履歴の取得、追加、反復、操作を行うためのメソッドを提供し、メッセージを特定の形式に変換するユーティリティや、
    ディープコピーのサポートも備えています。
    """

    def __init__(self, chat_id: UUID, kw_id: UUID | None) -> None:
        """
        新しい ChatHistory オブジェクトを初期化します。

        引数:
        - chat_id (UUID): チャットセッションの一意の識別子。
        - kw_id (UUID | None): チャットに関連する knowledge warehouse のオプション識別子。
        """

        self.id = chat_id
        self.kw_id = kw_id
        self._msgs: list[ChatMessage] = []

    def get_chat_history(self, newest_first: bool = False) -> List[ChatMessage]:
        """
        チャット履歴を取得します。オプションで逆時系列（最新のものが先）でソートできます。

        引数:
        - newest_first (bool, optional): True の場合、メッセージを逆順（最新のものが先）で返します。デフォルトは False。

        戻り値:
        - List[ChatMessage]: ソートされたチャットメッセージのリスト。
        """
        history = sorted(self._msgs, key=lambda msg: msg.message_time)
        if newest_first:
            return history[::-1]
        return history

    def __len__(self):
        return len(self._msgs)

    def append(self, langchain_msg: AIMessage | HumanMessage, metadata=None):
        """
        新しいメッセージをチャット履歴に追加します。

        引数:
        - langchain_msg (AIMessage | HumanMessage): メッセージの内容（AI または Human メッセージ）。
        - metadata (dict[str, Any], optional): メッセージに関連する追加のメタデータ。デフォルトは空の辞書です。
        """
        if metadata is None:
            metadata = {}
        chat_msg = ChatMessage(
            chat_id=self.id,
            message_id=uuid4(),
            kw_id=self.kw_id,
            msg=langchain_msg,
            message_time=datetime.now(),
            metadata=metadata,
        )
        self._msgs.append(chat_msg)

    def iter_pairs(self) -> Generator[Tuple[HumanMessage, AIMessage], None, None]:
        """
        チャット履歴をペアで反復処理し、HumanMessage の後に AIMessage を返します。

        戻り値:
        - Tuple[HumanMessage, AIMessage]: HumanMessage と AIMessage のペア。

        例外:
        - AssertionError: ペア内のメッセージが期待される順序（HumanMessage の後に AIMessage）でない場合に発生します。
        """
        # chat_history を逆順にして、最新のものが最初に来るようにします。
        it = iter(self.get_chat_history(newest_first=True))
        for ai_message, human_message in zip(it, it, strict=False):
            assert isinstance(
                human_message.msg, HumanMessage
            ), f"msg {human_message} is not HumanMessage"
            assert isinstance(
                ai_message.msg, AIMessage
            ), f"msg {ai_message} is not AIMessage"
            yield human_message.msg, ai_message.msg

    def to_list(self) -> List[HumanMessage | AIMessage]:
        """
        チャット履歴を HumanMessage または AIMessage オブジェクトのリストに変換します。

        戻り値:
        - list[HumanMessage | AIMessage]: メタデータなしの、rawの形式のメッセージのリスト。
        """

        return [_msg.msg for _msg in self._msgs]


@dataclass
class ChatHistoryInfo:
    nb_chats: int
    current_default_chat: UUID
    current_chat_history_length: int

    def add_to_tree(self, chats_tree: Tree):
        chats_tree.add(f"Number of Chats: [bold]{self.nb_chats}[/bold]")
        chats_tree.add(
            f"Current Default Chat: [bold magenta]{self.current_default_chat}[/bold magenta]"
        )
        chats_tree.add(
            f"Current Chat History Length: [bold]{self.current_chat_history_length}[/bold]"
        )
