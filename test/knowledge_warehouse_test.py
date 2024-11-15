import asyncio

from core.ai_core.knowledge_warehouse.knowledge_warehouse import KnowledgeWarehouse
from core.ai_core.storage.storage_builder import StorageBuilder, StorageType

def test_save():
    kw = KnowledgeWarehouse.from_files(name="Test Warehouse 1", file_paths=["test1.txt"], storage=StorageBuilder.build_storage(StorageType.LocalStorage,"/Users/squall/develop/knowledge warehouse/files", True))
    kw.print_info()
    asyncio.run(kw.save("/Users/squall/develop/knowledge warehouse"))

def test_load():
    kw = KnowledgeWarehouse.load("/Users/squall/develop/knowledge warehouse/kw_edc05ab7-faab-4952-9123-6276f865ec1f")
    kw.print_info()

    # response = kw.ask("イオンアイビス株式会社とイオンスマートテクノロジー株式会社の統合時期はいつですか？")

    # print(response.model_dump())
    # print(response.answer)


if __name__ == "__main__":
    # test_load()
    test_save()