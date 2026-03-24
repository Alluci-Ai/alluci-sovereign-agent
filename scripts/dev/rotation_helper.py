
import os
import secrets
import logging
from cryptography.fernet import Fernet
from dotenv import load_dotenv, set_key

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RotationHelper")

def rotate_keys():
    env_path = ".env"
    load_dotenv(env_path)

    old_master_key = os.getenv("POLYTOPE_MASTER_KEY")
    
    # 1. Generate NEW keys
    new_master_key = Fernet.generate_key().decode()
    new_jwt_secret = secrets.token_urlsafe(64)
    
    logger.info("Generated new security keys.")

    # 2. Update .env file
    set_key(env_path, "POLYTOPE_MASTER_KEY", new_master_key)
    set_key(env_path, "JWT_SECRET_KEY", new_jwt_secret)
    logger.info("Updated .env with new POLYTOPE_MASTER_KEY and JWT_SECRET_KEY.")

    # 3. Re-encrypt Vault
    try:
        from backend.security.vault import VaultManager
        if old_master_key:
            # We need to initialize vault with old key, then rotate to new
            vault = VaultManager(old_master_key)
            # Assuming VaultManager has a rotate_keys method as per documentation
            if hasattr(vault, "rotate_keys"):
                vault.rotate_keys(new_master_key)
                logger.info("Successfully re-encrypted vault with new master key.")
            else:
                logger.warning("VaultManager does not have rotate_keys method. Manual re-encryption might be required.")
    except Exception as e:
        logger.error(f"Failed to re-encrypt vault: {e}")

    logger.info("Rotation complete. Please restart the backend services.")

if __name__ == "__main__":
    rotate_keys()
