import pytest
from backend.services.scraper import fetch_and_extract_markdown
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_fetch_and_extract_markdown_github():
    with patch('httpx.AsyncClient') as mock_client:
        mock_instance = mock_client.return_value.__aenter__.return_value
        mock_resp = AsyncMock()
        mock_resp.text = "# Mocked Readme"
        mock_instance.get.return_value = mock_resp
        
        result = await fetch_and_extract_markdown("https://github.com/test/repo")
        assert "Mocked Readme" in result
        # Verify it hits the raw github URL
        mock_instance.get.assert_called_with("https://raw.githubusercontent.com/test/repo/main/README.md")

@pytest.mark.asyncio
async def test_fetch_and_extract_markdown_html():
    with patch('httpx.AsyncClient') as mock_client:
        mock_instance = mock_client.return_value.__aenter__.return_value
        mock_resp = AsyncMock()
        mock_resp.text = "<html><body><h1>Title</h1><p>Content goes here</p></body></html>"
        mock_instance.get.return_value = mock_resp
        
        result = await fetch_and_extract_markdown("https://example.com/docs")
        assert "Title" in result
        assert "Content goes here" in result
