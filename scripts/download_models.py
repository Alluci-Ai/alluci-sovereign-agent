import os
import sys
import logging
from huggingface_hub import snapshot_download

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ModelDownloader")

def download_models():
    """
    Automated CLI script to handle direct mirror_cache downloads.
    Scans the user's hardware tier and downloads the appropriate models.
    """
    # Ensure we can import from backend
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from backend.inference.profiler import HardwareProfiler
    from backend.config import settings
    
    logger.info("Initializing Hardware Scan...")
    profile = HardwareProfiler.get_system_profile()
    tier = profile.get("tier", "TIER_4_EDGE")
    recommended = profile.get("recommended_model", settings.LOCAL_MODEL_LITE)
    
    logger.info(f"Hardware Profile: {profile.get('os')} | RAM: {profile.get('ram_gb')}GB | GPU: {profile.get('vram_gb')}GB VRAM")
    logger.info(f"Assigned Tier: {tier}")
    logger.info(f"Recommended Primary Model: {recommended}")
    
    # We will download the primary model for the tier, plus the light model for background tasks if different
    models_to_download = [recommended]
    
    # Always ensure the LIGHT tier is available for background cognitive processes
    if settings.LOCAL_MODEL_LIGHT not in models_to_download:
        models_to_download.append(settings.LOCAL_MODEL_LIGHT)
        
    # The max model for when absolute maximum intelligence is requested
    if settings.LOCAL_MODEL_MAX not in models_to_download:
        models_to_download.append(settings.LOCAL_MODEL_MAX)
        
    cache_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'mirror_cache'))
    os.makedirs(cache_dir, exist_ok=True)
    
    logger.info(f"Downloading models to local cache: {cache_dir}")
    
    for model_name in models_to_download:
        # The model_name from profiler.py is the full repo_id (e.g. 'Alluci/alluci-polytope-gemma-4-31b-bf16')
        repo_id = model_name
        clean_name = model_name.split("/")[-1]
        local_path = os.path.join(cache_dir, clean_name)
        
        logger.info(f"Starting download for {repo_id}...")
        try:
            snapshot_download(
                repo_id=repo_id,
                local_dir=local_path
            )
            logger.info(f"Successfully downloaded {repo_id} to {local_path}")
        except Exception as e:
            logger.error(f"Failed to download {repo_id}: {e}")

if __name__ == "__main__":
    download_models()
