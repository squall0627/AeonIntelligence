from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from rich.tree import Tree

from core.ai_core.files.file import AIFile


@dataclass
class StorageInfo:
    storage_type: str
    n_files: int
    directory_path: str = None

    def add_to_tree(self, files_tree: Tree):
        files_tree.add(f"Storage Type: [italic]{self.storage_type}[/italic]")
        files_tree.add(f"Number of Files: [bold]{self.n_files}[/bold]")
        files_tree.add(f"Directory Path: [italic]{self.directory_path}[/italic]")


class StorageBase(ABC):
    """
    ストレージシステムの抽象基底クラス。すべてのサブクラスは、特定のプロパティを定義し、ファイル管理のための特定のメソッドを実装する必要があります。

    プロパティ:
    - name (str): ストレージタイプの名前。
    """

    name: str

    def __init_subclass__(cls, **kwargs):
        for required in ("name",):
            if not getattr(cls, required):
                raise TypeError(
                    f"Can't instantiate abstract class {cls.__name__} without {required} attribute defined"
                )
        return super().__init_subclass__(**kwargs)

    def __repr__(self) -> str:
        return f"storage_type: {self.name}"

    @abstractmethod
    def nb_files(self) -> int:
        """
        ストレージ内のファイル数を取得する抽象メソッド。

        戻り値:
        - int: ストレージ内のファイル数。

        例外:
        - Exception: メソッドが実装されていない場合。
        """
        raise Exception("Unimplemented nb_files method")

    @abstractmethod
    async def get_files(self) -> list[AIFile]:
        """
        ストレージ内のファイル `AIFile` を取得する抽象非同期メソッド。

        戻り値:
        - list[AIFile]: ストレージ内のファイル `AIFile` オブジェクトのリスト。

        例外:
        - Exception: メソッドが実装されていない場合。
        """
        raise Exception("Unimplemented get_files method")

    @abstractmethod
    async def upload_file(self, file: AIFile, exists_ok: bool = False) -> None:
        """
        ファイルをストレージにアップロードする抽象非同期メソッド。

        引数:
        - file (AIFile): アップロードするファイル。
        - exists_ok (bool): True の場合、ファイルが既に存在していても上書きを許可します。デフォルトは False。

        例外:
        - Exception: メソッドが実装されていない場合。
        """
        raise Exception("Unimplemented  upload_file method")

    @abstractmethod
    async def remove_file(self, file_id: UUID) -> None:
        """
        ストレージからファイルを削除する抽象非同期メソッド。

        引数:
        - file_id (UUID): 削除するファイルの一意の識別子。

        例外:
        - Exception: メソッドが実装されていない場合。
        """
        raise Exception("Unimplemented remove_file method")

    @abstractmethod
    def get_directory_path(self) -> str | None:
        """
        ストレージのディレクトリパスを取得する抽象プロパティ。

        戻り値:
        - str (str | None): ストレージのディレクトリパス。

        例外:
        - Exception: プロパティが実装されていない場合。
        """
        raise Exception("Unimplemented dir_path property")

    def info(self) -> StorageInfo:
        """
        ストレージの情報を返し、ストレージのタイプやファイル数を含みます。

        戻り値:
        - StorageInfo: ストレージの詳細を含むオブジェクト。
        """
        return StorageInfo(
            storage_type=self.name,
            n_files=self.nb_files(),
            directory_path=self.get_directory_path(),
        )
