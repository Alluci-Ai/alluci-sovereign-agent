# scripts/verify_local.py — Alluci Sovereign Doctor
import requests
import os
import sys
import subprocess
from dotenv import load_dotenv

load_dotenv(override=True)

def check_env():
    print("Checking environment variables...")
    required = ["POLYTOPE_MASTER_KEY", "JWT_SECRET_KEY", "CSRF_SECRET_KEY"]
    missing = [r for r in required if not os.getenv(r)]
    if missing:
        print(f"FAILED: Missing {missing} in .env")
        return False
    print("OK: Environment variables present.")
    return True

def check_backend():
    print("Checking Backend (8000)...")
    try:
        res = requests.get("http://127.0.0.1:8000/health", timeout=5)
        if res.status_code == 200:
            print("OK: Backend is reachable.")
            return True
        print(f"FAILED: Backend returned {res.status_code}")
    except Exception as e:
        print(f"FAILED: Backend unreachable: {e}")
    return False

def check_frontend():
    print("Checking Frontend (3000)...")
    try:
        res = requests.get("http://127.0.0.1:3000/", timeout=5)
        if res.status_code == 200:
            print("OK: Frontend is reachable.")
            return True
        print(f"FAILED: Frontend returned {res.status_code}")
    except Exception as e:
        print(f"FAILED: Frontend unreachable: {e}")
    return False

def check_deps():
    print("Checking Python dependencies...")
    try:
        subprocess.run(["pip", "check"], capture_output=True, check=True)
        print("OK: Python dependencies consistent.")
    except Exception:
        print("WARNING: Dependency conflicts detected. Run 'pip install -r requirements.txt'")

if __name__ == "__main__":
    print("Running Alluci Health Check...")
    e = check_env()
    b = check_backend()
    f = check_frontend()
    check_deps()
    
    if all([e, b, f]):
        print("\nSUCCESS: Alluci v6.4 is healthy and reachable!")
        sys.exit(0)
    else:
        print("\nERROR: Some checks failed. Use 'make start' to repair.")
        sys.exit(1)
