import importlib
import pkgutil
import threading
from typing import Type, Optional

from langchain_core.runnables.base import RunnableLike
from langchain_core.vectorstores import VectorStore

from core.ai_core.llm import LLMEndpoint
from core.ai_core.rag.config.ai_rag_config import RetrievalConfig
from core.ai_core.rag.node_functions.node_function_base import NodeFunctionBase


class NodeFunctionsFactory:
    _know_node_functions = None
    _lock = threading.RLock()

    @classmethod
    def _import_all_modules_in_package(cls, package_name: str):
        package = importlib.import_module(package_name)
        for _, module_name, _ in pkgutil.iter_modules(package.__path__):
            importlib.import_module(f"{package_name}.{module_name}")

    @classmethod
    def _load_all_node_functions(cls, base_class: Type[NodeFunctionBase]):
        with cls._lock:
            if cls._know_node_functions is None:
                # Initialize the known node functions
                cls._know_node_functions = {}

                # Import all modules in the package of the base class
                cls._import_all_modules_in_package(
                    "core.ai_core.rag.node_functions.impl"
                )

                # Load all node functions recursively
                cls._load_all_node_functions_recursively(base_class)
        return cls._know_node_functions

    @classmethod
    def _load_all_node_functions_recursively(cls, base_class: Type[NodeFunctionBase]):
        for subclass in base_class.__subclasses__():
            # Add the subclass to the known node functions
            cls._know_node_functions[getattr(subclass, "name")] = subclass
            cls._know_node_functions.update(
                cls._load_all_node_functions_recursively(subclass)
            )
        return cls._know_node_functions

    @classmethod
    def get_node_function(
        cls,
        name: str,
        retrieval_config: RetrievalConfig,
        llm: LLMEndpoint,
        vector_store: VectorStore | None = None,
    ) -> Optional[RunnableLike]:
        if not cls._know_node_functions or name not in cls._know_node_functions.keys():
            cls._load_all_node_functions(NodeFunctionBase)
        if name in cls._know_node_functions.keys():
            func_cls = cls._know_node_functions[name]
            func_obj = func_cls(
                retrieval_config=retrieval_config, llm=llm, vector_store=vector_store
            )
            return func_obj.arun if func_obj.is_async else func_obj.run
        else:
            raise ValueError(f"Node function {name} not found")
