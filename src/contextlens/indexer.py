from .embeddings.factory import EmbeddingFactory
import lancedb
import pandas as pd
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

import yaml

class ContextIndexer:
    def __init__(self, db_path: str = None, config_path: str = "contextlens_config.yaml"):
        if db_path is None:
            db_path = str(Path.home() / ".contextlens" / "db")
        
        # Load Config
        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        except Exception:
            self.config = {
                "embedding": {"engine_type": "local", "model_name": "all-MiniLM-L6-v2"},
                "indexing": {"chunk_size": 500, "overlap": 50}
            }

        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db = lancedb.connect(db_path)
        
        # Phase 1: Pluggable Embedding Pipeline (Config-Driven)
        emb_cfg = self.config.get("embedding", {})
        self.embedding_engine = EmbeddingFactory.get_engine(
            engine_type=emb_cfg.get("engine_type", "local"),
            model_name=emb_cfg.get("model_name")
        )
        
        # Phase 4: Memory Segmentation
        self.semantic_table = "semantic_knowledge"
        self.episodic_table = "episodic_timeline"
        
        self._init_tables()

    def _init_tables(self):
        existing_tables = self.db.table_names()
        
        for table_name in [self.semantic_table, self.episodic_table]:
            if table_name not in existing_tables:
                data = [{
                    "vector": self.embedding_engine.encode("initialization sequence"),
                    "text": "init",
                    "app_name": "system",
                    "window_title": "init",
                    "timestamp": datetime.now().isoformat(),
                    "metadata": "{}"
                }]
                self.db.create_table(table_name, data=data)

    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
        """Advanced semantic-aware chunking with sliding window overlap."""
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            if len(para) > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                start = 0
                while start < len(para):
                    end = start + chunk_size
                    chunk = para[start:end]
                    chunks.append(chunk.strip())
                    start += (chunk_size - overlap)
                continue

            if len(current_chunk) + len(para) < chunk_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                    current_chunk = overlap_text + "\n\n" + para + "\n\n"
                else:
                    current_chunk = para + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        return chunks

    def add_content(self, text: str, app_name: str, window_title: str, is_semantic: bool = False):
        """Add content to either Semantic or Episodic memory."""
        if not text.strip():
            return
        
        chunks = self._chunk_text(text)
        table_name = self.semantic_table if is_semantic else self.episodic_table
        table = self.db.open_table(table_name)
        
        payload = []
        for i, chunk in enumerate(chunks):
            embedding = self.embedding_engine.encode(chunk)
            payload.append({
                "vector": embedding,
                "text": chunk,
                "app_name": app_name,
                "window_title": window_title,
                "timestamp": datetime.now().isoformat(),
                "metadata": json.dumps({"chunk_id": i, "total_chunks": len(chunks)})
            })
        
        table.add(payload)

    def add_event(self, app_name: str, summary: str, action_type: str = "view"):
        """Record a lightweight 'event' in episodic memory."""
        table = self.db.open_table(self.episodic_table)
        
        data = [{
            "vector": self.embedding_engine.encode(summary),
            "text": summary,
            "app_name": app_name,
            "window_title": summary[:50],
            "timestamp": datetime.now().isoformat(),
            "metadata": json.dumps({"action_type": action_type, "is_event": True})
        }]
        table.add(data)

    def search(self, query: str, limit: int = 5, app_filter: str = None, hours_ago: int = None, search_semantic: bool = False):
        """Search across segmented memory tables."""
        query_vector = self.embedding_engine.encode(query)
        table_name = self.semantic_table if search_semantic else self.episodic_table
        table = self.db.open_table(table_name)
        
        search_query = table.search(query_vector).limit(limit)
        
        conditions = []
        if app_filter:
            conditions.append(f"app_name = '{app_filter}'")
        
        if hours_ago:
            threshold = (datetime.now() - timedelta(hours=hours_ago)).isoformat()
            conditions.append(f"timestamp >= '{threshold}'")
        
        if conditions:
            search_query = search_query.where(" AND ".join(conditions))
        
        results = search_query.to_pandas()
        return results.to_dict('records')

    def get_recent(self, limit: int = 5):
        """Retrieve the most recent indexed states from episodic memory."""
        table = self.db.open_table(self.episodic_table)
        results = table.to_pandas().sort_values(by="timestamp", ascending=False).head(limit)
        return results.to_dict('records')
