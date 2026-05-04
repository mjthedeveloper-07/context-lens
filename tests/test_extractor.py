import pytest
from unittest.mock import MagicMock, patch
from src.contextlens.extractor import ContextExtractor

def test_extractor_init():
    extractor = ContextExtractor()
    assert extractor.system in ["Darwin", "Windows", "Linux"]

@patch('src.contextlens.extractor.subprocess.run')
def test_extract_text_accessibility_darwin(mock_run):
    # Mocking macOS
    with patch('platform.system', return_value='Darwin'):
        extractor = ContextExtractor()
        mock_run.return_value = MagicMock(stdout="Mocked UI Text")
        text = extractor.extract_text_accessibility()
        assert text == "Mocked UI Text"

def test_markdown_extraction_logic():
    # We can test the markdown tool logic if it were in extractor, 
    # but currently it's in mcp_server. Let's stick to extractor for now.
    pass
