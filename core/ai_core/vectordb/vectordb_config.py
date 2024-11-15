from enum import Enum


class VectordbType(str, Enum):
    FaissCPU = "Faiss-CPU"
    FaissGPU = "Faiss-GPU"

def default_vectordb_type() -> VectordbType:
    return VectordbType.FaissCPU