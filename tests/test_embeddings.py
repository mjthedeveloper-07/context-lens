import pytest
import numpy as np
from src.contextlens.embeddings.factory import EmbeddingFactory
from src.contextlens.embeddings.base import BaseEmbeddingEngine

def test_embedding_factory_local():
    engine = EmbeddingFactory.get_engine("local")
    assert isinstance(engine, BaseEmbeddingEngine)
    
    text = "Hello ContextLens"
    vector = engine.encode(text)
    assert isinstance(vector, np.ndarray)
    assert len(vector) > 0

def test_embedding_factory_invalid():
    with pytest.raises(ValueError):
        EmbeddingFactory.get_engine("invalid_engine")
