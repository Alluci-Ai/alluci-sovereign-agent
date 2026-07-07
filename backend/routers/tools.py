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
    if category not in ["TOOL", "MCP"]:
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

@router.post("/tools/execute/{tool_id}")
async def execute_tool(tool_id: str, payload: Dict[str, Any] = Body(...)):
    """Executes a tool directly via the Orchestrator's Tool Action pipeline."""
    from .. import services
    if not services.orch:
        raise HTTPException(status_code=503, detail="Orchestrator not available")
    
    # Extract args from payload
    args = payload.get("args", {})
    origin = payload.get("origin", "api")
    override_tearing = payload.get("override_tearing", False)
    override_avl = payload.get("override_avl", False)
    
    try:
        result = await services.orch.execute_tool_action(
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
