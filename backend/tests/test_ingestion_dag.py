import pytest
import asyncio
from backend.services.ingestion_dag import IngestionDAG

@pytest.mark.asyncio
async def test_ingestion_dag_flow():
    from unittest.mock import AsyncMock, MagicMock
    
    mock_router = AsyncMock()
    # 1st call: classification -> return category
    # 2nd call: classification -> return category
    # 3rd call: extraction -> return specs
    # 4th call: extraction -> return specs
    # 5th call: synthesis -> return manifest
    mock_router.get_structured_plan.side_effect = [
        {"category": "REST_API"},
        {"category": "CLI_COMMAND"},
        {"specs": "API specs here"},
        {"specs": "CLI specs here"},
        {
            "name": "Test Tool", 
            "description": "Desc", 
            "category": "API", 
            "execution": {"type": "API"}
        }
    ]
    
    mock_scraper = AsyncMock()
    mock_scraper.fetch_all_markdown.return_value = ["Doc 1", "Doc 2"]
    
    dag = IngestionDAG(router=mock_router, scraper_service=mock_scraper)
    
    updates = []
    async for update in dag.run(["http://api.com", "http://cli.com"], user_prompt="test prompt"):
        updates.append(update)
        
    assert len(updates) > 5
    assert updates[0]["type"] == "progress"
    
    # Last update should be success
    success_update = updates[-1]
    assert success_update["type"] == "success"
    assert success_update["manifest"]["name"] == "Test Tool"
    
    assert mock_scraper.fetch_all_markdown.called
    assert mock_router.get_structured_plan.call_count == 5
