import os
import json
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Body
from ..logging_config import get_logger

logger = get_logger("ToolsRouter")
router = APIRouter(tags=["Tools Vault"])

TOOLS_DIR = "alluci_vault/tools"

@router.get("/tools")
async def get_all_tools():
    """Retrieve all dynamically loaded tools from the vault."""
    from .. import services
    if services.tool_manager:
        try:
            return await services.tool_manager.list_tools()
        except Exception as e:
            logger.error(f"Failed to list tools via ToolManager: {e}")
            
    tool_map = {}
    # Load core tools first
    CORE_DIR = "core_tools"
    if os.path.exists(CORE_DIR):
        for filename in os.listdir(CORE_DIR):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(CORE_DIR, filename), "r") as f:
                        tool = json.load(f)
                        tool_map[tool["id"]] = tool
                except Exception as e:
                    logger.error(f"Failed to load core tool {filename}: {e}")
                    
    # Load and override with vault tools
    if os.path.exists(TOOLS_DIR):
        for filename in os.listdir(TOOLS_DIR):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(TOOLS_DIR, filename), "r") as f:
                        tool = json.load(f)
                        tool_map[tool["id"]] = tool
                except Exception as e:
                    logger.error(f"Failed to load vault tool {filename}: {e}")
                    
    return list(tool_map.values())

@router.put("/tools/{tool_id}")
async def save_tool(tool_id: str, payload: Dict[str, Any] = Body(...)):
    """Creates or Updates a tool in the local vault."""
    # Enforce Tool Boundary
    category = payload.get("category", "TOOL")
    if category not in ["TOOL", "MCP", "API", "CLI", "RPC"]:
        raise HTTPException(status_code=400, detail="Cannot save non-TOOL category to Tools endpoint. Use /api/v1/skills")
        
    os.makedirs(TOOLS_DIR, exist_ok=True)
    
    # Secure the tool ID to prevent path traversal
    safe_id = "".join(c for c in tool_id if c.isalnum() or c in ("-", "_"))
    if not safe_id:
        raise HTTPException(status_code=400, detail="Invalid tool ID")
        
    file_path = os.path.join(TOOLS_DIR, f"{safe_id}.json")
    
    # Ensure ID matches
    payload["id"] = safe_id
    
    try:
        with open(file_path, "w") as f:
            json.dump(payload, f, indent=2)
        logger.info(f"Tool {safe_id} saved to vault.")
        
        # Sync to ToolManager if available
        from .. import services
        if services.tool_manager:
            await services.tool_manager.save_tool(payload)
            
        return {"status": "SUCCESS", "tool_id": safe_id}
    except Exception as e:
        logger.error(f"Failed to save tool {safe_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to write tool to vault")

@router.delete("/tools/{tool_id}")
async def delete_tool(tool_id: str):
    """Deletes a tool from the local vault."""
    safe_id = "".join(c for c in tool_id if c.isalnum() or c in ("-", "_"))
    file_path = os.path.join(TOOLS_DIR, f"{safe_id}.json")
    
    deleted = False
    if os.path.exists(file_path):
        os.remove(file_path)
        deleted = True
        logger.info(f"Tool {safe_id} deleted from disk.")
        
    # Sync to ToolManager if available
    from .. import services
    if services.tool_manager:
        manager_deleted = await services.tool_manager.delete_tool(safe_id)
        deleted = deleted or manager_deleted
        
    if deleted:
        return {"status": "SUCCESS"}
    raise HTTPException(status_code=404, detail="Tool not found")

@router.put("/tools/{tool_id}/toggle")
async def toggle_tool(tool_id: str, payload: Dict[str, bool] = Body(...)):
    """Toggles a tool's active state in the toggles.json configuration."""
    if "enabled" not in payload:
        raise HTTPException(status_code=400, detail="Missing 'enabled' field in payload")
    
    from ..state_manager import StateManager
    StateManager.set_tool_toggle(tool_id, payload["enabled"])
    logger.info(f"Tool {tool_id} toggled to {payload['enabled']}")
    return {"status": "SUCCESS", "tool_id": tool_id, "enabled": payload["enabled"]}

@router.post("/tools/execute/{tool_id}")
async def execute_tool(tool_id: str, payload: Dict[str, Any] = Body(...)):
    """Executes a tool directly via the Orchestrator's Tool Action pipeline."""
    from .. import services
    if not services.orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not available")
    
    # Extract args from payload
    args = payload.get("args", {})
    origin = payload.get("origin", "api")
    override_tearing = payload.get("override_tearing", False)
    override_avl = payload.get("override_avl", False)
    
    try:
        result = await services.orchestrator.execute_tool_action(
            tool_id=tool_id,
            args=args,
            origin=origin,
            override_tearing=override_tearing,
            override_avl=override_avl
        )
        return result
    except Exception as e:
        logger.error(f"Execution failed for tool {tool_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tools/fnd_tool_01/capability")
async def execute_fnd_tool_capability(payload: Dict[str, Any] = Body(...)):
    """Executes specific capabilities on the FounderNarrativeTool (fnd_tool_01)."""
    from .. import services
    from ..tools.founder_narrative_tool import FounderNarrativeTool

    capability = payload.get("capability")
    params = payload.get("params", {})

    tool_instance = FounderNarrativeTool(
        vault_manager=services.vault,
        exec_approval_mgr=getattr(services, "exec_approval_manager", None)
    )

    if capability == "transcribe_interview":
        file_path = params.get("file_path", "")
        return await tool_instance.transcribe_interview(file_path)
    elif capability == "audit_evidence":
        claims = params.get("claims", [])
        return tool_instance.audit_evidence(claims)
    elif capability == "request_approval":
        narrative_id = params.get("narrative_id", "v1")
        summary = params.get("context_summary", "")
        return await tool_instance.request_approval(narrative_id, summary)
    elif capability == "export_deliverables":
        narrative_data = params.get("narrative_data", {})
        company_name = params.get("company_name", "Company")
        return tool_instance.export_deliverables(narrative_data, company_name)
    elif capability == "sync_channels":
        channel = params.get("channel", "slack")
        sync_payload = params.get("payload", {})
        return await tool_instance.sync_external_channels(channel, sync_payload)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown capability: {capability}")

@router.post("/tools/fnd_tool_02/capability")
async def execute_fnd_tool_02_capability(payload: Dict[str, Any] = Body(...)):
    """Executes specific capabilities on the FounderInsightMarketShiftTool (fnd_tool_02)."""
    from .. import services
    from ..tools.founder_insight_market_shift_tool import FounderInsightMarketShiftTool

    capability = payload.get("capability")
    params = payload.get("params", {})

    tool_instance = FounderInsightMarketShiftTool(
        vault_manager=services.vault,
        exec_approval_mgr=getattr(services, "exec_approval_manager", None)
    )

    if capability == "extract_market_shifts":
        macro_inputs = params.get("macro_inputs", [])
        return tool_instance.extract_market_shifts(macro_inputs)
    elif capability == "score_decision_confidence":
        recommendation = params.get("recommendation", "")
        evidence_claims = params.get("evidence_claims", [])
        return tool_instance.score_decision_confidence(recommendation, evidence_claims)
    elif capability == "evaluate_signals_and_risks":
        current_state = params.get("current_state", {})
        market_signals = params.get("market_signals", [])
        return tool_instance.evaluate_signals_and_risks(current_state, market_signals)
    elif capability == "export_insight_assets":
        insight_data = params.get("insight_data", {})
        company_name = params.get("company_name", "Company")
        return tool_instance.export_insight_assets(insight_data, company_name)
    elif capability == "request_founder_signoff":
        insight_id = params.get("insight_id", "v1")
        summary = params.get("context_summary", "")
        return await tool_instance.request_founder_signoff(insight_id, summary)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown capability: {capability}")

@router.post("/tools/spe_tool_01/capability")
async def execute_spe_tool_capability(payload: Dict[str, Any] = Body(...)):
    """Executes specific capabilities on the StrategicPlanningExecutionTool (spe_tool_01)."""
    from .. import services
    from ..tools.strategic_planning_execution_tool import StrategicPlanningExecutionTool

    capability = payload.get("capability")
    params = payload.get("params", {})

    tool_instance = StrategicPlanningExecutionTool(
        vault_manager=services.vault,
        exec_approval_mgr=getattr(services, "exec_approval_manager", None)
    )

    if capability == "decompose_strategic_plan":
        pillars = params.get("pillars", [])
        return tool_instance.decompose_strategic_plan(pillars)
    elif capability == "calculate_project_health":
        projects = params.get("projects", [])
        return tool_instance.calculate_project_health(projects)
    elif capability == "generate_balanced_scorecard":
        kpi_metrics = params.get("kpis", [])
        return tool_instance.generate_balanced_scorecard(kpi_metrics)
    elif capability == "export_operating_system":
        plan_data = params.get("plan_data", {})
        company_name = params.get("company_name", "Company")
        return tool_instance.export_operating_system(plan_data, company_name)
    elif capability == "request_executive_approval":
        plan_id = params.get("plan_id", "v1")
        summary = params.get("context_summary", "")
        return await tool_instance.request_executive_approval(plan_id, summary)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown capability: {capability}")

@router.post("/tools/ir_tool_01/capability")
async def execute_ir_tool_capability(payload: Dict[str, Any] = Body(...)):
    """Executes specific capabilities on the InvestmentReadinessTool (ir_tool_01)."""
    from .. import services
    from ..tools.investment_readiness_tool import InvestmentReadinessTool

    capability = payload.get("capability")
    params = payload.get("params", {})

    tool_instance = InvestmentReadinessTool(
        vault_manager=services.vault,
        exec_approval_mgr=getattr(services, "exec_approval_manager", None)
    )

    if capability == "assess_readiness_gaps":
        inventory_data = params.get("inventory_data", {})
        return tool_instance.assess_readiness_gaps(inventory_data)
    elif capability == "audit_data_room_structure":
        folder_structure = params.get("folder_structure", {})
        return tool_instance.audit_data_room_structure(folder_structure)
    elif capability == "generate_investor_guide":
        company_name = params.get("company_name", "Company")
        data_room_structure = params.get("data_room_structure", {})
        return tool_instance.generate_investor_guide(company_name, data_room_structure)
    elif capability == "export_diligence_package":
        diligence_data = params.get("diligence_data", {})
        company_name = params.get("company_name", "Company")
        return tool_instance.export_diligence_package(diligence_data, company_name)
    elif capability == "request_publication_approval":
        data_room_id = params.get("data_room_id", "v1")
        summary = params.get("context_summary", "")
        return await tool_instance.request_publication_approval(data_room_id, summary)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown capability: {capability}")

@router.post("/tools/ldl_tool_01/capability")
async def execute_ldl_tool_capability(payload: Dict[str, Any] = Body(...)):
    """Executes specific capabilities on the LegalDocumentLifecycleTool (ldl_tool_01)."""
    from .. import services
    from ..tools.legal_document_lifecycle_tool import LegalDocumentLifecycleTool

    capability = payload.get("capability")
    params = payload.get("params", {})

    tool_instance = LegalDocumentLifecycleTool(
        vault_manager=services.vault,
        exec_approval_mgr=getattr(services, "exec_approval_manager", None)
    )

    if capability == "audit_legal_compliance":
        repository_data = params.get("repository_data", {})
        return tool_instance.audit_legal_compliance(repository_data)
    elif capability == "generate_legal_templates":
        doc_type = params.get("doc_type", "Mutual NDA")
        party_details = params.get("party_details", {})
        return tool_instance.generate_legal_templates(doc_type, party_details)
    elif capability == "verify_signature_status":
        contracts = params.get("contracts", [])
        return tool_instance.verify_signature_status(contracts)
    elif capability == "export_legal_repository":
        legal_data = params.get("legal_data", {})
        company_name = params.get("company_name", "Company")
        return tool_instance.export_legal_repository(legal_data, company_name)
    elif capability == "request_execution_signoff":
        contract_id = params.get("contract_id", "v1")
        summary = params.get("context_summary", "")
        return await tool_instance.request_execution_signoff(contract_id, summary)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown capability: {capability}")

@router.post("/tools/ocs_tool_01/capability")
async def execute_ocs_tool_capability(payload: Dict[str, Any] = Body(...)):
    """Executes specific capabilities on the OwnershipCapitalStrategyTool (ocs_tool_01)."""
    from .. import services
    from ..tools.ownership_capital_strategy_tool import OwnershipCapitalStrategyTool

    capability = payload.get("capability")
    params = payload.get("params", {})

    tool_instance = OwnershipCapitalStrategyTool(
        vault_manager=services.vault,
        exec_approval_mgr=getattr(services, "exec_approval_manager", None)
    )

    if capability == "audit_cap_table_ledger":
        cap_table_data = params.get("cap_table_data", {})
        return tool_instance.audit_cap_table_ledger(cap_table_data)
    elif capability == "model_dilution_scenarios":
        current_cap_table = params.get("current_cap_table", {})
        financing_round = params.get("financing_round", {})
        return tool_instance.model_dilution_scenarios(current_cap_table, financing_round)
    elif capability == "calculate_waterfall_payouts":
        cap_table_data = params.get("cap_table_data", {})
        exit_valuation = float(params.get("exit_valuation", 50000000.0))
        return tool_instance.calculate_waterfall_payouts(cap_table_data, exit_valuation)
    elif capability == "export_capital_strategy_package":
        strategy_data = params.get("strategy_data", {})
        company_name = params.get("company_name", "Company")
        return tool_instance.export_capital_strategy_package(strategy_data, company_name)
    elif capability == "request_cap_table_approval":
        cap_table_id = params.get("cap_table_id", "v1")
        summary = params.get("context_summary", "")
        return await tool_instance.request_cap_table_approval(cap_table_id, summary)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown capability: {capability}")

@router.post("/tools/suf_tool_01/capability")
async def execute_suf_tool_capability(payload: Dict[str, Any] = Body(...)):
    """Executes specific capabilities on the UseOfFundsCapitalAllocationTool (suf_tool_01)."""
    from .. import services
    from ..tools.use_of_funds_capital_allocation_tool import UseOfFundsCapitalAllocationTool

    capability = payload.get("capability")
    params = payload.get("params", {})

    tool_instance = UseOfFundsCapitalAllocationTool(
        vault_manager=services.vault,
        exec_approval_mgr=getattr(services, "exec_approval_manager", None)
    )

    if capability == "audit_capital_allocation":
        budget_actuals_data = params.get("budget_actuals_data", {})
        return tool_instance.audit_capital_allocation(budget_actuals_data)
    elif capability == "calculate_runway_and_burn":
        financial_metrics = params.get("financial_metrics", {})
        return tool_instance.calculate_runway_and_burn(financial_metrics)
    elif capability == "validate_funds_compliance":
        allocation_plan = params.get("allocation_plan", {})
        investor_covenants = params.get("investor_covenants", {})
        return tool_instance.validate_funds_compliance(allocation_plan, investor_covenants)
    elif capability == "export_capital_allocation_package":
        allocation_data = params.get("allocation_data", {})
        company_name = params.get("company_name", "Company")
        return tool_instance.export_capital_allocation_package(allocation_data, company_name)
    elif capability == "request_allocation_approval":
        reallocation_id = params.get("reallocation_id", "v1")
        summary = params.get("context_summary", "")
        return await tool_instance.request_allocation_approval(reallocation_id, summary)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown capability: {capability}")

@router.post("/tools/swd_tool_01/capability")
async def execute_swd_tool_capability(payload: Dict[str, Any] = Body(...)):
    """Executes specific capabilities on the StrategicWorkforceDesignTool (swd_tool_01)."""
    from .. import services
    from ..tools.strategic_workforce_design_tool import StrategicWorkforceDesignTool

    capability = payload.get("capability")
    params = payload.get("params", {})

    tool_instance = StrategicWorkforceDesignTool(
        vault_manager=services.vault,
        exec_approval_mgr=getattr(services, "exec_approval_manager", None)
    )

    if capability == "map_business_capabilities":
        work_tasks = params.get("work_tasks", [])
        return tool_instance.map_business_capabilities(work_tasks)
    elif capability == "analyze_resource_optimization":
        capabilities_list = params.get("capabilities_list", [])
        return tool_instance.analyze_resource_optimization(capabilities_list)
    elif capability == "calculate_ai_token_tco":
        workforce_model = params.get("workforce_model", {})
        return tool_instance.calculate_ai_token_tco(workforce_model)
    elif capability == "export_workforce_package":
        workforce_data = params.get("workforce_data", {})
        company_name = params.get("company_name", "Company")
        return tool_instance.export_workforce_package(workforce_data, company_name)
    elif capability == "request_workforce_approval":
        plan_id = params.get("plan_id", "v1")
        summary = params.get("context_summary", "")
        return await tool_instance.request_workforce_approval(plan_id, summary)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown capability: {capability}")

@router.post("/tools/okd_tool_01/capability")
async def execute_okd_tool_capability(payload: Dict[str, Any] = Body(...)):
    """Executes specific capabilities on the OrganizationalKnowledgeDocumentTool (okd_tool_01)."""
    from .. import services
    from ..tools.organizational_knowledge_document_tool import OrganizationalKnowledgeDocumentTool

    capability = payload.get("capability")
    params = payload.get("params", {})

    tool_instance = OrganizationalKnowledgeDocumentTool(
        vault_manager=services.vault,
        exec_approval_mgr=getattr(services, "exec_approval_manager", None)
    )

    if capability == "audit_knowledge_repository":
        knowledge_data = params.get("knowledge_data", {})
        return tool_instance.audit_knowledge_repository(knowledge_data)
    elif capability == "index_document_metadata":
        document_input = params.get("document_input", {})
        return tool_instance.index_document_metadata(document_input)
    elif capability == "query_organizational_memory":
        search_query = params.get("search_query", "")
        return tool_instance.query_organizational_memory(search_query)
    elif capability == "export_knowledge_package":
        knowledge_payload = params.get("knowledge_payload", {})
        company_name = params.get("company_name", "Company")
        return tool_instance.export_knowledge_package(knowledge_payload, company_name)
    elif capability == "request_knowledge_approval":
        update_id = params.get("update_id", "v1")
        summary = params.get("context_summary", "")
        return await tool_instance.request_knowledge_approval(update_id, summary)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown capability: {capability}")

@router.post("/tools/cmp_tool_01/capability")
async def execute_cmp_tool_capability(payload: Dict[str, Any] = Body(...)):
    """Executes specific capabilities on the CompensationStrategyTool (cmp_tool_01)."""
    from .. import services
    from ..tools.compensation_strategy_tool import CompensationStrategyTool

    capability = payload.get("capability")
    params = payload.get("params", {})

    tool_instance = CompensationStrategyTool(
        vault_manager=services.vault,
        exec_approval_mgr=getattr(services, "exec_approval_manager", None)
    )

    if capability == "audit_compensation_bands":
        salary_benchmark_data = params.get("salary_benchmark_data", {})
        return tool_instance.audit_compensation_bands(salary_benchmark_data)
    elif capability == "model_equity_incentives":
        option_grant_data = params.get("option_grant_data", {})
        return tool_instance.model_equity_incentives(option_grant_data)
    elif capability == "calculate_total_rewards_tco":
        rewards_payload = params.get("rewards_payload", {})
        return tool_instance.calculate_total_rewards_tco(rewards_payload)
    elif capability == "export_compensation_package":
        compensation_payload = params.get("compensation_payload", {})
        company_name = params.get("company_name", "Company")
        return tool_instance.export_compensation_package(compensation_payload, company_name)
    elif capability == "request_compensation_approval":
        grant_id = params.get("grant_id", "v1")
        summary = params.get("context_summary", "")
        return await tool_instance.request_compensation_approval(grant_id, summary)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown capability: {capability}")

@router.post("/tools/fde_tool_01/capability")
async def execute_fde_tool_capability(payload: Dict[str, Any] = Body(...)):
    """Executes specific capabilities on the FounderEducationDecisionTool (fde_tool_01)."""
    from .. import services
    from ..tools.founder_education_decision_tool import FounderEducationDecisionTool

    capability = payload.get("capability")
    params = payload.get("params", {})

    tool_instance = FounderEducationDecisionTool(
        vault_manager=services.vault,
        exec_approval_mgr=getattr(services, "exec_approval_manager", None)
    )

    if capability == "synthesize_learning_modules":
        topic_scope = params.get("topic_scope", {})
        return tool_instance.synthesize_learning_modules(topic_scope)
    elif capability == "evaluate_decision_confidence":
        decision_scenario = params.get("decision_scenario", {})
        return tool_instance.evaluate_decision_confidence(decision_scenario)
    elif capability == "log_decision_journal_entry":
        journal_payload = params.get("journal_payload", {})
        return tool_instance.log_decision_journal_entry(journal_payload)
    elif capability == "export_education_package":
        education_payload = params.get("education_payload", {})
        company_name = params.get("company_name", "Company")
        return tool_instance.export_education_package(education_payload, company_name)
    elif capability == "request_decision_signoff":
        decision_id = params.get("decision_id", "v1")
        summary = params.get("context_summary", "")
        return await tool_instance.request_decision_signoff(decision_id, summary)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown capability: {capability}")

@router.post("/tools/ftl_tool_01/capability")
async def execute_ftl_tool_capability(payload: Dict[str, Any] = Body(...)):
    """Executes specific capabilities on the FoundingTeamLeadershipTool (ftl_tool_01)."""
    from .. import services
    from ..tools.founding_team_leadership_tool import FoundingTeamLeadershipTool

    capability = payload.get("capability")
    params = payload.get("params", {})

    tool_instance = FoundingTeamLeadershipTool(
        vault_manager=services.vault,
        exec_approval_mgr=getattr(services, "exec_approval_manager", None)
    )

    if capability == "audit_leadership_architecture":
        team_data = params.get("team_data", {})
        return tool_instance.audit_leadership_architecture(team_data)
    elif capability == "model_founder_equity_vesting":
        founder_equity_data = params.get("founder_equity_data", {})
        return tool_instance.model_founder_equity_vesting(founder_equity_data)
    elif capability == "calculate_leadership_capacity_tco":
        leadership_payload = params.get("leadership_payload", {})
        return tool_instance.calculate_leadership_capacity_tco(leadership_payload)
    elif capability == "export_leadership_package":
        leadership_payload = params.get("leadership_payload", {})
        company_name = params.get("company_name", "Company")
        return tool_instance.export_leadership_package(leadership_payload, company_name)
    elif capability == "request_leadership_approval":
        arch_id = params.get("arch_id", "v1")
        summary = params.get("context_summary", "")
        return await tool_instance.request_leadership_approval(arch_id, summary)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown capability: {capability}")

@router.post("/tools/hro_tool_01/capability")
async def execute_hro_tool_capability(payload: Dict[str, Any] = Body(...)):
    """Executes specific capabilities on the HumanResourceOnboardingTool (hro_tool_01)."""
    from .. import services
    from ..tools.human_resource_onboarding_tool import HumanResourceOnboardingTool

    capability = payload.get("capability")
    params = payload.get("params", {})

    tool_instance = HumanResourceOnboardingTool(
        vault_manager=services.vault,
        exec_approval_mgr=getattr(services, "exec_approval_manager", None)
    )

    if capability == "audit_onboarding_pipeline":
        onboarding_data = params.get("onboarding_data", {})
        return tool_instance.audit_onboarding_pipeline(onboarding_data)
    elif capability == "generate_onboarding_roadmap":
        employee_input = params.get("employee_input", {})
        return tool_instance.generate_onboarding_roadmap(employee_input)
    elif capability == "calculate_time_to_productivity":
        productivity_metrics = params.get("productivity_metrics", {})
        return tool_instance.calculate_time_to_productivity(productivity_metrics)
    elif capability == "export_onboarding_package":
        onboarding_payload = params.get("onboarding_payload", {})
        company_name = params.get("company_name", "Company")
        return tool_instance.export_onboarding_package(onboarding_payload, company_name)
    elif capability == "request_onboarding_approval":
        onboarding_id = params.get("onboarding_id", "v1")
        summary = params.get("context_summary", "")
        return await tool_instance.request_onboarding_approval(onboarding_id, summary)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown capability: {capability}")

@router.post("/tools/agentic_registration_tool_01/capability")
async def execute_agentic_registration_capability(payload: Dict[str, Any] = Body(...)):
    """Executes specific capabilities on the AgenticRegistrationTool (agentic_registration_tool_01)."""
    from .. import services
    from ..tools.agentic_registration_tool import AgenticRegistrationTool

    capability = payload.get("capability")
    params = payload.get("params", {})

    tool_instance = AgenticRegistrationTool(
        vault_manager=services.vault,
        exec_approval_mgr=getattr(services, "exec_approval_manager", None)
    )

    if capability == "discover_agent_auth_metadata":
        target_domain = params.get("target_domain", "example.com")
        return await tool_instance.discover_agent_auth_metadata(target_domain)
    elif capability == "register_agent_identity":
        target_domain = params.get("target_domain", "example.com")
        registration_payload = params.get("registration_payload", {})
        return await tool_instance.register_agent_identity(target_domain, registration_payload)
    elif capability == "poll_claim_ceremony":
        target_domain = params.get("target_domain", "example.com")
        claim_token = params.get("claim_token", "")
        token_endpoint = params.get("token_endpoint", "")
        interval = int(params.get("interval", 5))
        return await tool_instance.poll_claim_ceremony(target_domain, claim_token, token_endpoint, interval)
    elif capability == "exchange_token_jwt_bearer":
        token_endpoint = params.get("token_endpoint", "")
        identity_assertion = params.get("identity_assertion", "")
        target_domain = params.get("target_domain", "example.com")
        return await tool_instance.exchange_token_jwt_bearer(token_endpoint, identity_assertion, target_domain)
    elif capability == "revoke_agent_token":
        target_domain = params.get("target_domain", "example.com")
        token = params.get("token", "")
        token_type_hint = params.get("token_type_hint", "access_token")
        return await tool_instance.revoke_agent_token(target_domain, token, token_type_hint)
    elif capability == "export_registration_package":
        registration_payload = params.get("registration_payload", {})
        company_name = params.get("company_name", "Company")
        return tool_instance.export_registration_package(registration_payload, company_name)
    elif capability == "request_registration_approval":
        registration_id = params.get("registration_id", "v1")
        summary = params.get("context_summary", "")
        return await tool_instance.request_registration_approval(registration_id, summary)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown capability: {capability}")

@router.post("/tools/test_sandbox")
async def test_sandbox(payload: Dict[str, Any] = Body(...)):
    """Executes a tool dynamically without permanently saving it to the registry."""
    from .. import services
    from ..security.guardrail import GuardrailScanner
    from ..inference.router import ModelRouter
    from ..config import settings
    import platform
    import subprocess
    
    manifest = payload.get("manifest", {})
    test_params = payload.get("params", {})
    
    if not manifest:
        raise HTTPException(status_code=400, detail="Missing tool manifest")
        
    # Pre-Execution Scanning (AVL/PPN)
    scanner = GuardrailScanner(ModelRouter(settings=settings, vault=services.vault))
    safe, msg = await scanner.scan_input(json.dumps(payload))
    if not safe:
        logger.critical(f"Topological Rupture Detected in Sandbox: {msg}")
        raise HTTPException(status_code=403, detail=f"Topological Rupture: {msg}")
        
    execution_config = manifest.get("execution", {})
    tool_type = execution_config.get("type", manifest.get("category"))
    
    # Retrieve Secrets Ephemerally
    auth_headers_id = execution_config.get("authHeadersVaultId")
    env_vars_ids = execution_config.get("envVarsVaultId", {})
    
    env_vars = os.environ.copy() if tool_type == "CLI" else {}
    if services.vault:
        if auth_headers_id:
            secret_data = await services.vault.retrieve_secret(auth_headers_id)
            if secret_data and "secret" in secret_data:
                # API context
                logger.info("Injecting vaulted auth headers ephemerally...")
        
        for k, v_id in env_vars_ids.items():
            secret_data = await services.vault.retrieve_secret(v_id)
            if secret_data and "secret" in secret_data:
                env_vars[k] = secret_data["secret"]
    
    
    if tool_type == "CLI":
        cmd = execution_config.get("command", execution_config.get("path"))
        if not cmd:
            raise HTTPException(status_code=400, detail="Missing command or path for CLI execution")
            
        system = platform.system()
        try:
            if system == "Darwin":
                sb_profile = "(version 1)\n(deny default)\n(allow process-exec)\n(allow network-outbound)"
                process = subprocess.run(
                    ["sandbox-exec", "-p", sb_profile, cmd],
                    input=json.dumps(test_params).encode(),
                    env=env_vars,
                    capture_output=True,
                    timeout=10
                )
            else:
                process = subprocess.run(
                    [cmd],
                    input=json.dumps(test_params).encode(),
                    env=env_vars,
                    capture_output=True,
                    timeout=10
                )
                
            return {
                "status": "SUCCESS",
                "output": process.stdout.decode(),
                "error": process.stderr.decode(),
                "code": process.returncode
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
            
    elif tool_type == "API":
        import httpx
        import re
        
        base_url = execution_config.get("baseUrl", "").rstrip("/")
        endpoint = execution_config.get("endpoint", "")
        method = execution_config.get("method", "GET").upper()
        
        # Inject path parameters
        url = base_url + endpoint
        for k, v in test_params.items():
            url = re.sub(rf"{{{k}}}", str(v), url)
            
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                req_kwargs = {"headers": env_vars}
                if method in ("GET", "DELETE"):
                    req_kwargs["params"] = test_params
                else:
                    req_kwargs["json"] = test_params
                    
                resp = await client.request(method, url, **req_kwargs)
                return {
                    "status": "SUCCESS" if resp.is_success else "ERROR",
                    "output": resp.text,
                    "code": resp.status_code
                }
            except Exception as e:
                return {"status": "ERROR", "output": str(e), "code": 500}
                
    elif tool_type == "MCP":
        endpoint = execution_config.get("endpoint", "")
        if not endpoint:
            return {"status": "ERROR", "output": "Missing MCP endpoint", "code": 400}
            
        if endpoint.startswith("http"):
            import httpx
            async with httpx.AsyncClient(timeout=15.0) as client:
                try:
                    resp = await client.post(endpoint, json=test_params, headers=env_vars)
                    return {
                        "status": "SUCCESS" if resp.is_success else "ERROR",
                        "output": resp.text,
                        "code": resp.status_code
                    }
                except Exception as e:
                    return {"status": "ERROR", "output": str(e), "code": 500}
        else:
            try:
                import shlex
                process = subprocess.run(
                    shlex.split(endpoint),
                    input=json.dumps(test_params).encode(),
                    env=env_vars,
                    capture_output=True,
                    timeout=10
                )
                return {
                    "status": "SUCCESS" if process.returncode == 0 else "ERROR",
                    "output": process.stdout.decode() or process.stderr.decode(),
                    "code": process.returncode
                }
            except Exception as e:
                return {"status": "ERROR", "output": str(e), "code": 500}
    else:
        return {"status": "SUCCESS", "message": f"{tool_type} execution simulated"}

@router.post("/tools/ingest")
async def ingest_tool(payload: Dict[str, Any] = Body(...)):
    """Ingests an OpenAPI or MCP spec, or uses Smart Ingestion DAG for multi-url docs."""
    import httpx
    
    ingest_type = payload.get("type", "openapi")
    
    if ingest_type == "smart_ingest":
        from sse_starlette.sse import EventSourceResponse
        from ..ingestion_services.ingestion_dag import IngestionDAG
        from ..inference.router import ModelRouter
        from ..config import settings
        from .. import services
        import json
        import backend.ingestion_services.scraper as scraper_module
        
        urls = payload.get("urls", [])
        user_prompt = payload.get("user_prompt", "")
        deep_crawl = payload.get("deep_crawl", False)
        
        if not urls or not isinstance(urls, list) or not all(isinstance(u, str) and u.startswith("http") for u in urls):
            raise HTTPException(status_code=400, detail="urls must be a non-empty list of valid HTTP strings")
            
        async def event_generator():
            try:
                router_inst = ModelRouter(settings=settings, vault=services.vault)
                dag = IngestionDAG(router=router_inst, scraper_service=scraper_module)
                
                async for update in dag.run(urls, user_prompt, deep_crawl=deep_crawl):
                    yield json.dumps(update)
            except Exception as e:
                logger.error(f"DAG execution failed: {e}")
                yield json.dumps({"type": "error", "message": str(e)})

        return EventSourceResponse(event_generator())
        
    # Legacy handling for openapi and mcp_sse
    url = payload.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="Missing URL")
            
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            res = await client.get(url)
            res.raise_for_status()
            
            # Content-Type guard: detect non-JSON responses and reroute to Smart Ingestion
            content_type = res.headers.get("content-type", "")
            is_json = "application/json" in content_type or "application/openapi" in content_type
            
            # Also try to parse as JSON — some servers don't set Content-Type correctly
            if not is_json:
                try:
                    data = res.json()
                    is_json = True
                except Exception:
                    is_json = False
            else:
                data = res.json()
            
            if not is_json:
                # Reroute to Smart Ingestion DAG automatically
                logger.info(f"Non-JSON response from {url} (Content-Type: {content_type}). Rerouting to Smart Ingestion DAG.")
                from sse_starlette.sse import EventSourceResponse
                from ..ingestion_services.ingestion_dag import IngestionDAG
                from ..inference.router import ModelRouter
                from ..config import settings
                from .. import services
                import json as json_mod
                import backend.ingestion_services.scraper as scraper_module
                
                async def event_generator_reroute():
                    try:
                        router_inst = ModelRouter(settings=settings, vault=services.vault)
                        dag = IngestionDAG(router=router_inst, scraper_service=scraper_module)
                        async for update in dag.run([url], "", deep_crawl=False):
                            yield json_mod.dumps(update)
                    except Exception as e:
                        logger.error(f"Rerouted DAG execution failed: {e}")
                        yield json_mod.dumps({"type": "error", "message": str(e)})
                
                return EventSourceResponse(event_generator_reroute())
            
            manifest = {
                "name": data.get("info", {}).get("title", "Auto Ingested Tool"),
                "description": data.get("info", {}).get("description", "Ingested from " + url),
                "category": "API" if ingest_type == "openapi" else "MCP",
                "execution": {
                    "type": "API" if ingest_type == "openapi" else "MCP",
                },
                "schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
            
            if ingest_type == "openapi":
                servers = data.get("servers", [])
                if servers:
                    manifest["execution"]["baseUrl"] = servers[0].get("url", "")
                
                # Basic mapping of the first POST/GET route as an example
                paths = data.get("paths", {})
                for path, methods in paths.items():
                    for method, details in methods.items():
                        manifest["execution"]["endpoint"] = path
                        manifest["execution"]["method"] = method.upper()
                        # Extract basic schema from first path
                        break
                    break
                    
            return {"status": "SUCCESS", "manifest": manifest}
    except Exception as e:
        logger.error(f"Ingestion failed for {url}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

OAUTH_STATUS_CACHE = {}

@router.post("/tools/oauth2/device-auth")
async def initiate_device_auth(payload: Dict[str, str] = Body(...)):
    """Initiates RFC 8628 Device Authorization Grant."""
    target_domain = payload.get("target_domain")
    if not target_domain:
        raise HTTPException(status_code=400, detail="target_domain required")
        
    from ..auth.autonomous_discoverer import AlluciAutonomousDiscoverer
    import httpx
    
    discoverer = AlluciAutonomousDiscoverer()
    clean_domain = target_domain.rstrip('/')
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            result = await discoverer.execute_user_claimed_fallback(client, clean_domain, clean_domain)
            if result.get("status") == "authorization_pending":
                device_code = result.get("device_code")
                if device_code:
                    OAUTH_STATUS_CACHE[device_code] = "pending"
                    
                import asyncio
                from ..adapters.agentic_registration import AgenticRegistrationAdapter
                adapter = AgenticRegistrationAdapter()
                
                async def poll_wrapper():
                    try:
                        await adapter._poll_for_token(result, clean_domain)
                        if device_code:
                            OAUTH_STATUS_CACHE[device_code] = "success"
                    except Exception as e:
                        logger.error(f"Background polling failed: {e}")
                        if device_code:
                            OAUTH_STATUS_CACHE[device_code] = "error"
                            
                asyncio.create_task(poll_wrapper())
                return result
            else:
                raise HTTPException(status_code=400, detail="Failed to initiate device grant")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@router.get("/tools/oauth2/status")
async def check_oauth2_status(device_code: str):
    """Checks the local cache to see if the background poller succeeded."""
    status = OAUTH_STATUS_CACHE.get(device_code, "pending")
    return {"status": status}
