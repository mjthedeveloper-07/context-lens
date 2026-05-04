from sentence_transformers import SentenceTransformer
from .base import BaseEmbeddingEngine
import numpy as np

class LocalEmbeddingEngine(BaseEmbeddingEngine):
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)
        self._dimension = self.model.get_embedding_dimension()

    def encode(self, text: str) -> np.ndarray:
        return self.model.encode(text)

    @property
    def dimension(self) -> int:
        return self._dimension
