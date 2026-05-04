import lancedb
import pandas as pd
from sentence_transformers import SentenceTransformer
import os
import json
from datetime import datetime
from pathlib import Path

class ContextIndexer:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = str(Path.home() / ".contextlens" / "db")
        
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db = lancedb.connect(db_path)
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.table_name = "window_content"
        self._init_table()

    def _init_table(self):
        if self.table_name not in self.db.table_names():
            data = [{
                "vector": self.model.encode("dummy text"),
                "text": "dummy text",
                "app_name": "system",
                "window_title": "init",
                "timestamp": datetime.now().isoformat(),
                "chunk_id": 0,
                "metadata": "{}"
            }]
            self.db.create_table(self.table_name, data=data)

    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
        """Advanced semantic-aware chunking with sliding window overlap."""
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            # If paragraph itself is too large, break it down
            if len(para) > chunk_size:
                # Add current_chunk first if it exists
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                # Break down large paragraph
                start = 0
                while start < len(para):
                    end = start + chunk_size
                    chunk = para[start:end]
                    chunks.append(chunk.strip())
                    # Move start forward by chunk_size minus overlap
                    start += (chunk_size - overlap)
                continue

            if len(current_chunk) + len(para) < chunk_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    # Start new chunk with the last part of the previous chunk for overlap
                    overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                    current_chunk = overlap_text + "\n\n" + para + "\n\n"
                else:
                    current_chunk = para + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        return chunks

    def add_content(self, text: str, app_name: str, window_title: str):
        if not text.strip():
            return
        
        # Implement RAG Refinement: Chunking
        chunks = self._chunk_text(text)
        table = self.db.open_table(self.table_name)
        
        payload = []
        for i, chunk in enumerate(chunks):
            embedding = self.model.encode(chunk)
            payload.append({
                "vector": embedding,
                "text": chunk,
                "app_name": app_name,
                "window_title": window_title,
                "timestamp": datetime.now().isoformat(),
                "chunk_id": i,
                "metadata": json.dumps({"total_chunks": len(chunks)})
            })
        
        table.add(payload)

    def search(self, query: str, limit: int = 5, app_filter: str = None):
        query_vector = self.model.encode(query)
        table = self.db.open_table(self.table_name)
        
        search_query = table.search(query_vector).limit(limit)
        if app_filter:
            search_query = search_query.where(f"app_name = '{app_filter}'")
        
        results = search_query.to_pandas()
        return results.to_dict('records')
