import os
import shutil

from typing import Set, Self
from pathlib import Path
from uuid import UUID

from core.ai_core.files.file import AIFile
from core.ai_core.knowledge_warehouse.serialization import LocalStorageConfig
from core.ai_core.storage.storage_base import StorageBase


class LocalStorage(StorageBase):
    """
    StorageBase クラスを具現化した LocalStorage は、ファイルをローカルディスクに保存するための実装です。このクラスはファイルのアップロード管理、ファイルハッシュの追跡、および指定されたディレクトリからの保存ファイルの取得を行います。

    プロパティ:
    - name (str): ストレージタイプの名前で、"local_storage" に設定されています。
    - files (list[AIFile]): このローカルストレージに保存されているファイルのリスト。
    - hashes (Set[str]): アップロードされたファイルの SHA-1 ハッシュのセット。
    - copy_flag (bool): True の場合、ファイルはストレージディレクトリにコピーされます。False の場合はシンボリックリンクが使用されます。
    - dir_path (Path): ファイルが保存されているディレクトリパス。

    引数:
    - dir_path (Path | None): オプションでファイルを保存するディレクトリパスを指定できます。デフォルトは環境変数 `AI_LOCAL_STORAGE` または `~/.cache/ai/files`。
    - copy_flag (bool): ファイルをコピーするかシンボリックリンクを作成するかの設定。デフォルトは True。
    """

    name: str = "local_storage"

    def __init__(self, dir_path: Path | None = None, copy_flag: bool = True):
        self.files: list[AIFile] = []
        self.hashes: Set[str] = set()
        self.copy_flag = copy_flag

        if dir_path is None:
            self.dir_path = Path(
                os.getenv("AI_LOCAL_STORAGE", "~/.cache/ai/files")
            )
        else:
            self.dir_path = dir_path
        os.makedirs(self.dir_path, exist_ok=True)

    def nb_files(self) -> int:
        return len(self.files)

    async def get_files(self) -> list[AIFile]:
        return self.files

    async def upload_file(self, file: AIFile, exists_ok: bool = False) -> None:
        dst_dir = os.path.join(self.dir_path, str(file.kw_id))
        dst_path = os.path.join(dst_dir, f"{file.file_id}{file.file_extension.value}")

        if file.file_sha1 in self.hashes and not exists_ok:
            raise FileExistsError(f"file {file.original_filename} already uploaded")

        # Ensure the destination directory exists
        os.makedirs(dst_dir, exist_ok=True)

        if self.copy_flag:
            shutil.copy2(file.path, dst_path)
        else:
            os.symlink(file.path, dst_path)

        file.path = Path(dst_path)
        self.files.append(file)
        self.hashes.add(file.file_sha1)

    async def remove_file(self, file_id: UUID) -> None:
        # delete file from storage
        for file in self.files:
            if file.file_id == file_id:
                if self.copy_flag:
                    os.remove(file.path)  # Remove actual file
                else:
                    os.unlink(file.path)  # Remove symbolic link
                self.files.remove(file)
                self.hashes.discard(file.file_sha1)
                break

    def get_directory_path(self) -> str | None:
        return str(self.dir_path)

    @classmethod
    def load(cls, config: LocalStorageConfig) -> Self:
        t_storage = cls(dir_path=config.storage_path)
        t_storage.files = [AIFile.deserialize(f) for f in config.files.values()]
        return t_storage

    def save(self) -> LocalStorageConfig:
        return LocalStorageConfig(
            storage_path=self.dir_path,
            files={f.file_id: f.serialize() for f in self.files},
       )