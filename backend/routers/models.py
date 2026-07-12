import os
import httpx
import asyncio
from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from ..security.auth import verify_authenticated
from ..security.oauth_store import oauth_store
from ..config import settings
from ..database import engine as db_engine
from sqlmodel import Session
from ..logging_config import get_logger
from .. import services

logger = get_logger("ModelsRouter")

router = APIRouter(tags=["Engine Models"])

async def fetch_openai_models(api_key: str) -> List[Dict[str, str]]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            if resp.status_code == 200:
                data = resp.json()
                return [{"id": m["id"], "name": m["id"], "category": "API"} for m in data.get("data", []) if "gpt" in m["id"] or "o1" in m["id"]]
    except Exception as e:
        logger.error(f"Failed to fetch OpenAI models: {e}")
    return []

async def fetch_openrouter_models(api_key: str) -> List[Dict[str, str]]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            if resp.status_code == 200:
                data = resp.json()
                return [{"id": m["id"], "name": m["name"], "category": "Open"} for m in data.get("data", [])]
    except Exception as e:
        logger.error(f"Failed to fetch OpenRouter models: {e}")
    return []

async def fetch_groq_models(api_key: str) -> List[Dict[str, str]]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            if resp.status_code == 200:
                data = resp.json()
                return [{"id": m["id"], "name": m["id"], "category": "API"} for m in data.get("data", [])]
    except Exception as e:
        logger.error(f"Failed to fetch Groq models: {e}")
    return []

async def scan_local_models() -> List[Dict[str, str]]:
    local_models = []
    
    # Check common MLX / HF cache or model_forge directories
    forge_path = os.path.join(os.getcwd(), "mirror_cache")
    if os.path.exists(forge_path):
        for item in os.listdir(forge_path):
            if os.path.isdir(os.path.join(forge_path, item)) and not item.startswith("."):
                if item in ("llama.cpp", "scripts", "tmp"):
                    continue
                name = item
                upper_name = name.upper()
                if "TIER-5" in upper_name or "TIER 5" in upper_name or "TIER5" in upper_name:
                    name = "Local Model Edge"
                elif "TIER-4" in upper_name or "TIER 4" in upper_name or "TIER4" in upper_name:
                    name = "Local Model Lite"
                local_models.append({"id": f"local/{item}", "name": name, "category": "Local"})
                
    # Always include the built-in Alluci Polytope Gemma 4 models from settings
    builtin_models = [
        {"id": f"local/{settings.LOCAL_MODEL_MAX}", "name": "Polytope Gemma 4 Max (31B BF16)", "category": "Local"},
        {"id": f"local/{settings.LOCAL_MODEL_STRONG}", "name": "Polytope Gemma 4 Strong (31B 8bit)", "category": "Local"},
        {"id": f"local/{settings.LOCAL_MODEL_MEDIUM}", "name": "Polytope Gemma 4 Medium (26B 4bit)", "category": "Local"},
        {"id": f"local/{settings.LOCAL_MODEL_LIGHT}", "name": "Polytope Gemma 4 Light (12B 4bit)", "category": "Local"},
        {"id": f"local/{settings.LOCAL_MODEL_LITE}", "name": "Polytope Gemma 4 Edge (2B 4bit)", "category": "Local"}
    ]
    
    existing_ids = {m["id"] for m in local_models}
    for m in builtin_models:
        if m["id"] not in existing_ids:
            local_models.append(m)
            
    # We can also add Ollama local scan if needed by checking `ollama list` output
    # but for now we stick to simple directory scanning as requested.
    return local_models

@router.get("/available", dependencies=[Depends(verify_authenticated)])
async def get_available_models():
    """
    Dynamically fetches available models from active API keys and local hardware.
    """
    available_models = []
    
    # Local Scan
    available_models.extend(await scan_local_models())
    
    # Pull API Keys from Sovereign Vault or env
    vault_keys = {}
    if getattr(services, "vault", None):
        keys = await services.vault.retrieve_secret("alluci_api_keys") or {}
        vault_keys = keys.get("llm", {})
        
    tasks = []
    
    # OpenAI
    openai_key = vault_keys.get("openai") or getattr(settings, "OPENAI_API_KEY", None)
    if openai_key:
        tasks.append(fetch_openai_models(openai_key))
        
    # OpenRouter
    openrouter_key = vault_keys.get("openrouter") or getattr(settings, "OPENROUTER_API_KEY", None)
    if openrouter_key:
        tasks.append(fetch_openrouter_models(openrouter_key))
        
    # Groq
    groq_key = vault_keys.get("groq") or getattr(settings, "GROQ_API_KEY", None)
    if groq_key:
        tasks.append(fetch_groq_models(groq_key))
        
    # Gather async API calls
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, list):
                available_models.extend(res)
                
    # Add Anthropic and Gemini manually if APIs don't easily provide them (Anthropic does but requires specific headers)
    anthropic_key = vault_keys.get("anthropic") or getattr(settings, "ANTHROPIC_API_KEY", None)
    if anthropic_key:
        available_models.extend([
            {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet", "category": "API"},
            {"id": "claude-3-haiku-20240307", "name": "Claude 3 Haiku", "category": "API"},
            {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus", "category": "API"}
        ])
        
    gemini_key = vault_keys.get("googleCloud") or getattr(settings, "GEMINI_API_KEY", None)
    if gemini_key:
        available_models.extend([
            {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro", "category": "API"},
            {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash", "category": "API"}
        ])
        
    return {"models": available_models}
