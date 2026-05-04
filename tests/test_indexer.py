import pytest
import os
import shutil
from src.contextlens.indexer import ContextIndexer

@pytest.fixture
def temp_indexer(tmp_path):
    db_path = str(tmp_path / "test_db")
    # Create a dummy config if needed or pass path
    indexer = ContextIndexer(db_path=db_path)
    yield indexer
    # Cleanup happens automatically with tmp_path

def test_chunk_text(temp_indexer):
    text = "Paragraph 1\n\nParagraph 2 with more text to test the chunking strategy of ContextLens."
    chunks = temp_indexer._chunk_text(text, chunk_size=50, overlap=10)
    assert len(chunks) >= 2
    assert "Paragraph 1" in chunks[0]

def test_init_tables(temp_indexer):
    tables = temp_indexer.db.list_tables()
    # list_tables() returns a ListTablesResponse in newer versions
    table_list = tables if isinstance(tables, list) else getattr(tables, "tables", [])
    assert "semantic_knowledge" in table_list
    assert "episodic_timeline" in table_list
    assert "agent_annotations" in table_list

def test_add_and_search_semantic(temp_indexer):
    temp_indexer.add_content("This is a semantic fact.", "AppA", "TitleA", is_semantic=True)
    results = temp_indexer.search("semantic fact", search_semantic=True)
    assert len(results) > 0
    assert results[0]["app_name"] == "AppA"
