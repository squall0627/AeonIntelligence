import asyncio
from importlib.metadata import files

from transformers import AutoTokenizer

from core.ai_core.knowledge_warehouse.knowledge_warehouse import KnowledgeWarehouse
from core.ai_core.llm import LLMEndpoint
from core.ai_core.llm.llm_config import LLMEndpointConfig, DefaultModelSuppliers, LLMName
from core.ai_core.storage.storage_builder import StorageBuilder, StorageType

def test_save():
    kw = KnowledgeWarehouse.from_files(name="Test Warehouse 1", file_paths=["test1.txt"], storage=StorageBuilder.build_storage(StorageType.LocalStorage,"/Users/squall/develop/knowledge warehouse/files", True))
    kw.print_info()
    asyncio.run(kw.save("/Users/squall/develop/knowledge warehouse"))

def test_load():
    kw = KnowledgeWarehouse.load("/Users/squall/develop/knowledge warehouse/kw_59dc69fa-c4b2-4271-8b79-91e35388c9ce")

    # llm = LLMEndpoint.from_config(
    #     LLMEndpointConfig(supplier=DefaultModelSuppliers.META, model=LLMName.llama3_2_vision_11b)
    # )
    # kw.llm = llm

    kw.print_info()

    # response = kw.ask("イオンアイビス株式会社とイオンスマートテクノロジー株式会社の統合時期はいつですか？", rag_pipeline=AiQARAG)
    response = kw.ask("イオンスマートテクノロジー株式会社をご紹介ください。")

    print(response.model_dump())
    print(response.answer)


if __name__ == "__main__":
    test_load()
    # test_save()
    # tokenizer = AutoTokenizer.from_pretrained("Xenova/mistral-tokenizer-v3")