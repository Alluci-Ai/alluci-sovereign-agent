#!/usr/bin/env python3
import uvicorn
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("========================================")
print("🧠 Sovereign Brain Daemon Boot Sequence Initiated...")
print("========================================")
print("Notice: The standalone daemon has been integrated into the Executive Orchestrator.")
print("Booting the Unified Backend API & Cognitive Engine...")
print("This will auto-connect the zero-lag iMessage bridge and apply all Soul settings.")
print("========================================")

if __name__ == "__main__":
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, log_level="info")
