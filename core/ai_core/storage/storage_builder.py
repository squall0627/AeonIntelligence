from typing import TypeAlias, Callable

from core.ai_core.knowledge_warehouse.serialization import StorageConfig
from core.ai_core.storage.local_storage import LocalStorage
from core.ai_core.storage.storage_base import StorageBase
from core.ai_core.storage.storage_config import StorageType, default_storage_type
from core.ai_core.storage.transparent_storage import TransparentStorage

StorageMapping: TypeAlias = dict[StorageType, Callable[[str, bool], StorageBase]]


class StorageBuilder:
    KNOWN_STORAGE: StorageMapping = {
        StorageType.TransparentStorage: (
            lambda dir_path, copy_flag: TransparentStorage()
        ),
        StorageType.LocalStorage: (
            lambda dir_path, copy_flag: LocalStorage(dir_path, copy_flag)
        ),
    }

    @classmethod
    def build_default_storage(
        cls, dir_path: str | None, copy_flag: bool | None
    ) -> StorageBase:
        return cls.build_storage(default_storage_type(), dir_path, copy_flag)

    @classmethod
    def build_storage(
        cls, storage_type: StorageType, dir_path: str | None, copy_flag: bool | None
    ) -> StorageBase:
        if storage_type not in cls.KNOWN_STORAGE:
            raise NotImplementedError(f"Storage type {storage_type} not implemented")
        else:
            return cls.KNOWN_STORAGE[storage_type](dir_path, copy_flag)

    @classmethod
    def load_storage(cls, config: StorageConfig) -> StorageBase:
        if config.storage_type not in cls.KNOWN_STORAGE:
            raise ValueError(f"Unknown storage type: {config.storage_type}")
        else:
            if config.storage_type == StorageType.LocalStorage:
                return LocalStorage.load(config)
            elif config.storage_type == StorageType.TransparentStorage:
                return TransparentStorage.load(config)
            else:
                raise NotImplementedError(
                    f"Storage type {config.storage_type} not implemented"
                )

    @classmethod
    def save_storage(cls, storage: StorageBase) -> StorageConfig:
        if isinstance(storage, LocalStorage):
            return storage.save()
        elif isinstance(storage, TransparentStorage):
            return storage.save()
        else:
            raise Exception("can't serialize storage. not supported for now")
