import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from backend.adapters.deep_research import (
    DeepResearchQueryExpansionAdapter,
    DeepResearchHarvestAdapter,
    DeepResearchEvaluateAdapter
)

@pytest.mark.asyncio
async def test_deep_research_query_expansion(temp_db):
    adapter = DeepResearchQueryExpansionAdapter()
    
    # Test missing queries
    res = await adapter.execute({})
    assert res.get("status") == "error"
    
    # Test successful query
    with patch("backend.adapters.deep_research.DDGS") as mock_ddgs, \
         patch("backend.adapters.search.SearXNGClient.search", new_callable=AsyncMock) as mock_sx, \
         patch("backend.adapters.search.NativeMultiEngineScraper.search", new_callable=AsyncMock) as mock_scraper, \
         patch("backend.adapters.deep_research._fetch_open_apis", new_callable=AsyncMock) as mock_apis:
        mock_instance = MagicMock()
        mock_ddgs.return_value.__enter__.return_value = mock_instance
        mock_instance.text.return_value = [
            {"href": "https://example.com/1"}
        ]
        mock_sx.return_value = {"urls": ["https://example.com/1"]}
        mock_scraper.return_value = {"urls": ["https://example.com/2"]}
        mock_apis.return_value = {"urls": []}
        
        res = await adapter.execute({"queries": ["test query"]})
        assert res.get("status") == "success"
        assert len(res["urls"]) >= 1
        assert "https://example.com/1" in res["urls"]

@pytest.mark.asyncio
async def test_deep_research_harvest(temp_db):
    adapter = DeepResearchHarvestAdapter()
    
    # Test missing urls
    res = await adapter.execute({})
    assert res.get("status") == "error"
    
    # Test successful harvest
    with patch("backend.adapters.deep_research.httpx.AsyncClient") as mock_client, \
         patch("backend.adapters.deep_research.trafilatura.extract") as mock_extract:
        
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        
        mock_response = MagicMock()
        mock_response.text = "<html>Test HTML</html>"
        mock_instance.get.return_value = mock_response
        
        mock_extract.return_value = "# Test Content"
        
        res = await adapter.execute({"urls": ["https://example.com/1"]})
        assert res.get("status") == "success"
        assert "--- SOURCE: https://example.com/1 ---" in res["harvested_content"]
        assert "# Test Content" in res["harvested_content"]

@pytest.mark.asyncio
async def test_deep_research_evaluate(temp_db):
    adapter = DeepResearchEvaluateAdapter()
    
    # Test missing dependency output
    res = await adapter.execute({})
    assert "Error: No dependency output provided" in res
    
    with patch("backend.services.router", new_callable=AsyncMock) as mock_router, \
         patch("backend.services.hlsm_manager", new_callable=AsyncMock) as mock_hlsm, \
         patch("backend.services.pcl", new_callable=AsyncMock) as mock_pcl:
        
        mock_router.get_response.return_value = "Final Evaluated Report"
        
        res = await adapter.execute({"dependency_output": "raw data from harvesting"})
        
        assert res == "Final Evaluated Report"
        
        # Verify get_response was called correctly
        mock_router.get_response.assert_awaited()
        
        await adapter._notify_pcl(mock_pcl, "Final Evaluated Report")
        
        mock_hlsm.encode_message.assert_awaited_once_with(
            content="Final Evaluated Report",
            source="deep_research",
            session_key="background_research",
            psi=0.5
        )

@pytest.mark.asyncio
async def test_deep_research_orchestration_rocco_routing(temp_db):
    from backend.engine.planner import Planner
    from backend.engine.executor import Executor
    from backend.adapters.registry import AdapterRegistry
    from backend.models import TaskStatus
    
    # 1. Routing (Planner)
    mock_router = AsyncMock()
    planner = Planner(router=mock_router)
    
    # "mode=research" triggers the deep research skill/tool routing
    # "agent_id='rocco'" assigns the tasks to the deep research sub-agent 'Rocco'
    dag = await planner.generate_plan(
        objective="Analyze AI agent architectures",
        mode="research",
        agent_id="rocco"
    )
    
    # Verify Routing created 3 steps correctly assigned to Rocco
    assert len(dag) == 3
    assert dag["task_research_1"].action == "deep_research_query_expansion"
    assert dag["task_research_1"].assignee == "rocco"
    assert dag["task_research_2"].action == "deep_research_harvest"
    assert dag["task_research_2"].assignee == "rocco"
    assert dag["task_research_3"].action == "deep_research_evaluate"
    assert dag["task_research_3"].assignee == "rocco"
    
    # 2. Orchestration (Executor)
    registry = AdapterRegistry()
    
    from backend.adapters.base import Adapter

    class MockAdapter(Adapter):
        def __init__(self, name, ret_val):
            self.name = name
            self.description = f"Mock adapter for {name}"
            self.ret_val = ret_val
            self.executed = False
        async def execute(self, args):
            self.executed = True
            return self.ret_val
            
    mock_expansion = MockAdapter("deep_research_query_expansion", {"urls": ["https://test.com"]})
    mock_harvest = MockAdapter("deep_research_harvest", {"harvested_content": "dummy html"})
    mock_evaluate = MockAdapter("deep_research_evaluate", "Final Orchestrated Report")
    
    registry.register(mock_expansion)
    registry.register(mock_harvest)
    registry.register(mock_evaluate)
    
    mock_session_factory = MagicMock()
    
    import sys
    mock_tracing = MagicMock()
    mock_span = MagicMock()
    mock_tracing.get_tracer.return_value.start_as_current_span.return_value.__enter__.return_value = mock_span
    
    mock_sql_session = MagicMock()
    mock_sql_session.return_value.__enter__.return_value.exec.return_value.first.return_value = None
    
    with patch.dict(sys.modules, {"backend.tracing_config": mock_tracing}), \
         patch("sqlmodel.Session", mock_sql_session):
        # Initialize Executor with mocked tracking
        executor = Executor(
            adapter_registry=registry,
            session_factory=mock_session_factory,
            max_concurrent=2
        )
        executor._init_task_records = MagicMock()
        executor._update_task_record = MagicMock()
        
        # Mock dependencies that might fail
        executor.supervisor = MagicMock()
        executor.supervisor.condense_context.side_effect = lambda x: x
        
        executor.watch_auth = MagicMock()
        executor.watch_auth.locked = False
        executor.watch_auth.verify_liveness.return_value = True
        
        # Execute the DAG via the Orchestrator's execution engine
        executed_dag = await executor.execute_dag(run_id=999, tasks=dag)
    
    # 3. Verify Orchestration results
    assert executed_dag["task_research_1"].status == TaskStatus.COMPLETED
    assert executed_dag["task_research_2"].status == TaskStatus.COMPLETED
    assert executed_dag["task_research_3"].status == TaskStatus.COMPLETED
    
    # Verify execution was called
    assert mock_expansion.executed
    assert mock_harvest.executed
    assert mock_evaluate.executed
