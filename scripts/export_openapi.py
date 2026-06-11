#!/usr/bin/env python3
"""
Extract the OpenAPI JSON schema from the Alluci Sovereign Agent backend.
This bypasses the disabled /docs endpoint to generate static documentation safely.
"""

import json
import os
import sys

# Ensure backend module can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from backend.app import app
except ImportError as e:
    print(f"Error importing FastAPI app: {e}")
    sys.exit(1)

def export_openapi():
    # Grab the OpenAPI schema directly from the FastAPI instance
    openapi_schema = app.openapi()
    
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Documentation")
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, "openapi.json")
    
    with open(output_path, "w") as f:
        json.dump(openapi_schema, f, indent=2)
        
    print(f"OpenAPI schema successfully exported to {output_path}")

if __name__ == "__main__":
    export_openapi()
