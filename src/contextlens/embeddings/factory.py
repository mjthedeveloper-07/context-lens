from .local import LocalEmbeddingEngine
from .base import BaseEmbeddingEngine
from typing import Dict, Type

class EmbeddingFactory:
    _engines: Dict[str, Type[BaseEmbeddingEngine]] = {
        "local": LocalEmbeddingEngine
    }

    @classmethod
    def get_engine(cls, engine_type: str = "local", model_name: str = None, **kwargs) -> BaseEmbeddingEngine:
        engine_cls = cls._engines.get(engine_type)
        if not engine_cls:
            raise ValueError(f"Unknown embedding engine type: {engine_type}")
        
        if engine_type == "local" and model_name:
            return engine_cls(model_name=model_name, **kwargs)
            
        return engine_cls(**kwargs)
