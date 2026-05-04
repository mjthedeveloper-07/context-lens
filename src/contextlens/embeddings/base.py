from abc import ABC, abstractmethod
import numpy as np

class BaseEmbeddingEngine(ABC):
    @abstractmethod
    def encode(self, text: str) -> np.ndarray:
        """Encode a single string into a vector."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the dimension of the generated vectors."""
        pass
