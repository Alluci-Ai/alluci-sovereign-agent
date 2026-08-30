import pytest
from backend.ingestion_services.scraper import fetch_and_extract_markdown
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
        mock_resp.text = "<html><head><title>Deep Research Guide</title></head><body><main><article><h1>Deep Research Guide</h1><p>Comprehensive article content goes here for testing markdown extraction and paragraph parsing across large documents. This paragraph contains sufficient tokens and words to satisfy the length threshold required for clean production distillation without triggering fallback renderers.</p></article></main></body></html>"
        mock_instance.get.return_value = mock_resp
        
        result = await fetch_and_extract_markdown("https://example.com/docs")
        assert "Deep Research Guide" in result or "Comprehensive article content" in result


@pytest.mark.asyncio
async def test_web_search_multi_query_execution(tmp_path):
    from backend.adapters.web_search import WebSearchAdapter

    db_file = str(tmp_path / "test_research.db")
    adapter = WebSearchAdapter(provider="ddg", db_path=db_file)

    with patch.object(adapter, "execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.side_effect = [
            {"status": "success", "results": [{"title": "Spec 1", "link": "https://a.com/1", "snippet": "Snippet 1"}]},
            {"status": "success", "results": [{"title": "Spec 2", "link": "https://a.com/2", "snippet": "Snippet 2"}]}
        ]

        res = await adapter.execute_multi_query(["query A", "query B"])
        assert res["status"] == "success"
        assert len(res["results"]) == 2
        assert res["results"][0]["title"] == "Spec 1"
        assert res["results"][1]["title"] == "Spec 2"


@pytest.mark.asyncio
async def test_research_dossier_sqlite_caching(tmp_path):
    from backend.adapters.web_search import ResearchDossierCache, WebSearchAdapter

    db_file = str(tmp_path / "cache_test.db")
    cache = ResearchDossierCache(db_path=db_file)

    sample_results = [{"title": "MLX Docs", "link": "https://mlx.org", "snippet": "MLX guide"}]
    cache.set("Apple MLX 2026", sample_results)

    cached_val = cache.get("Apple MLX 2026")
    assert cached_val is not None
    assert cached_val[0]["title"] == "MLX Docs"

    # Verify WebSearchAdapter uses cache for 0ms retrieval
    adapter = WebSearchAdapter(provider="ddg", db_path=db_file)
    harvest_res = await adapter.expand_and_harvest("Apple MLX 2026")
    assert harvest_res["status"] == "success"
    assert harvest_res["provider"] == "local_sqlite_cache"
    assert harvest_res["results"][0]["title"] == "MLX Docs"
