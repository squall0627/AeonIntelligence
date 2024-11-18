from langchain_core.vectorstores import VectorStore


class AIRagRetriever:
    def __init__(
            self,
            vector_store: VectorStore | None = None,
    ):
        self.vector_store = vector_store

    def get_retriever(self, **kwargs):
        if self.vector_store:
            retriever = self.vector_store.as_retriever(**kwargs)
        else:
            raise ValueError("No vector store provided")

        return retriever