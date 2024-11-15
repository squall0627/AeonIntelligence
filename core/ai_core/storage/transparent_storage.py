from typing import Self
from uuid import UUID

from core.ai_core.files.file import AIFile
from core.ai_core.knowledge_warehouse.serialization import TransparentStorageConfig
from core.ai_core.storage.storage_base import StorageBase


class TransparentStorage(StorageBase):
    """
    StorageBase クラスを具現化した TransparentStorage は、ファイルをメモリに保存するための実装です。このクラスはファイルのアップロード管理を行います。

    プロパティ:
    - name (str): ストレージタイプの名前で、"transparent_storage" に設定されています。
    - id_files (dict[str, AIFile]): メモリに保存されているファイルのリスト。
    """

    name: str = "transparent_storage"

    def __init__(self):
        self.id_files = {}

    def nb_files(self) -> int:
        return len(self.id_files)

    async def get_files(self) -> list[AIFile]:
        return list(self.id_files.values())

    async def upload_file(self, file: AIFile, exists_ok: bool = False) -> None:
        # TODO ファイル名が既に存在する場合の処理
        self.id_files[file.file_id] = file

    async def remove_file(self, file_id: UUID) -> None:
        # TODO
        raise NotImplementedError

    def get_directory_path(self) -> str | None:
        return None

    @classmethod
    def load(cls, config: TransparentStorageConfig) -> Self:
        t_storage = cls()
        t_storage.id_files = {
            i: AIFile.deserialize(f) for i, f in config.files.items()
        }
        return t_storage

    def save(self) -> TransparentStorageConfig:
        return TransparentStorageConfig(files={f.file_id: f.serialize() for f in self.id_files.values()})