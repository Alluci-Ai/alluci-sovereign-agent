import pytest
import os
from pathlib import Path
from backend.tools.strategic_planning_execution_tool import StrategicPlanningExecutionTool
from backend.tool_manager import ToolManager
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_decompose_strategic_plan():
    tool = StrategicPlanningExecutionTool(vault_manager=None, exec_approval_mgr=None)
    pillars = [
        {
            "title": "Product Leadership",
            "objectives": [
                {
                    "title": "Deploy Alluci Sovereign Agent v1",
                    "initiatives": [
                        {
                            "title": "Build Core Execution Tools",
                            "projects": [
                                {
                                    "title": "Build SPE Tool",
                                    "owner": "Lead Engineer",
                                    "milestones": ["Specification", "Implementation", "Testing"],
                                    "tasks": ["Task 1", "Task 2"]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    ]

    res = tool.decompose_strategic_plan(pillars)
    assert res["status"] == "SUCCESS"
    assert res["pillars_count"] == 1
    assert res["total_projects"] == 1
    assert res["total_milestones"] == 3
    assert res["total_tasks"] == 2


@pytest.mark.asyncio
async def test_calculate_project_health():
    tool = StrategicPlanningExecutionTool(vault_manager=None, exec_approval_mgr=None)
    projects = [
        {"title": "Project Alpha", "progress_pct": 100, "elapsed_days": 10, "planned_days": 10},
        {"title": "Project Beta", "progress_pct": 50, "elapsed_days": 15, "planned_days": 30},
        {"title": "Project Gamma", "progress_pct": 10, "elapsed_days": 20, "planned_days": 30},
        {"title": "Project Delta", "progress_pct": 40, "elapsed_days": 35, "planned_days": 30}
    ]

    res = tool.calculate_project_health(projects)
    assert res["status"] == "SUCCESS"
    assert res["total_projects_evaluated"] == 4
    assert res["health_state_distribution"]["Met"] == 1
    assert res["health_state_distribution"]["On Track"] == 1
    assert res["health_state_distribution"]["At Risk"] == 1
    assert res["health_state_distribution"]["Overdue"] == 1


@pytest.mark.asyncio
async def test_generate_balanced_scorecard():
    tool = StrategicPlanningExecutionTool(vault_manager=None, exec_approval_mgr=None)
    kpis = [
        {"pillar": "Financial", "name": "ARR", "actual": 1200000, "target": 1000000, "weight": 2.0},
        {"pillar": "Customer", "name": "NPS", "actual": 75, "target": 80, "weight": 1.0},
        {"pillar": "Operations", "name": "Uptime", "actual": 99.9, "target": 99.9, "weight": 1.5}
    ]

    res = tool.generate_balanced_scorecard(kpis)
    assert res["status"] == "SUCCESS"
    assert res["total_kpis_evaluated"] == 3
    assert len(res["balanced_scorecard"]["Financial"]) == 1
    assert res["balanced_scorecard"]["Financial"][0]["achievement_pct"] == 120.0


@pytest.mark.asyncio
async def test_export_operating_system(tmp_path):
    tool = StrategicPlanningExecutionTool(vault_manager=None, exec_approval_mgr=None)
    tool.output_base_dir = tmp_path / "deliverables"

    plan_payload = {
        "pillars": ["Product Excellence", "Enterprise Growth"],
        "initiatives": [
            {"title": "Launch SPE Skill & Tool", "owner": "Core Team", "status": "Complete", "progress": 100}
        ]
    }

    res = tool.export_operating_system(plan_payload, company_name="ExecCo")
    assert res["status"] == "SUCCESS"
    assert res["files_generated_count"] >= 6
    assert os.path.exists(res["export_directory"])

    exp_dir = Path(res["export_directory"])
    assert (exp_dir / "Strategic_Operating_Plan.md").exists()
    assert (exp_dir / "Work_Breakdown_Structure.json").exists()
    assert (exp_dir / "Balanced_Scorecard.json").exists()
    assert (exp_dir / "Executive_Dashboard.html").exists()
    assert (exp_dir / "Project_Plan_Export.csv").exists()
    assert (exp_dir / "Risk_And_Decision_Register.md").exists()


@pytest.mark.asyncio
async def test_spe_01_tool_manifest_discovery():
    mock_vault = AsyncMock()
    mock_vault.retrieve_secret.return_value = {}
    tm = ToolManager(vault=mock_vault)
    tools = await tm.list_tools()
    spe_tool = [t for t in tools if t.get("id") == "spe_tool_01"]
    assert len(spe_tool) > 0
    assert spe_tool[0]["name"] == "Strategic Planning, Execution & Performance Tool"
