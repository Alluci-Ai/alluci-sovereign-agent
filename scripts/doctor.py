#!/usr/bin/env python3
import os
import sys
import socket
import logging
import importlib.util

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("alluci-doctor")

def check_env_var(name, critical=False):
    val = os.getenv(name)
    if val:
        logger.info(f"✅ {name} is set.")
        return True
    else:
        if critical:
            logger.error(f"❌ {name} is MISSING (CRITICAL).")
        else:
            logger.warning(f"⚠️ {name} is not set (Optional).")
        return False

def check_package(name):
    if importlib.util.find_spec(name):
        logger.info(f"✅ Package '{name}' is installed.")
        return True
    else:
        logger.error(f"❌ Package '{name}' is MISSING.")
        return False

def check_port(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            logger.info(f"✅ Port {port} is available.")
            return True
        except socket.error:
            logger.warning(f"⚠️ Port {port} is ALREADY IN USE.")
            return False

def main():
    logger.info("--- Alluci Sovereign Agent System Doctor ---")
    
    # 1. Check Critical Env Vars
    critical_vars = ["POLYTOPE_MASTER_KEY", "JWT_SECRET_KEY"]
    for v in critical_vars:
        check_env_var(v, critical=True)
    
    # 2. Check Optional Env Vars (Example providers)
    optional_vars = ["GOOGLE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "REDIS_URL", "DATABASE_URL"]
    for v in optional_vars:
        check_env_var(v)
        
    # 3. Check Critical Dependencies
    critical_pkgs = ["fastapi", "sqlmodel", "pydantic", "fastapi_csrf_protect", "secure", "zeroconf", "playwright"]
    for p in critical_pkgs:
        check_package(p.replace("-", "_"))
        
    # 4. Check Ports
    check_port(8000) # Backend
    
    logger.info("--- Diagnostic Complete ---")

if __name__ == "__main__":
    main()
