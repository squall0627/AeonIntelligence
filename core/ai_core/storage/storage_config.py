from enum import Enum


class StorageType(str, Enum):
    TransparentStorage = "transparent_storage"
    LocalStorage = "local_storage"

def default_storage_type() -> StorageType:
    return StorageType.TransparentStorage