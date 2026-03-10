#!/usr/bin/env python3
import requests
import json
import time
import argparse
import sys
import os

# Try to load master key from .env
def get_auth_token():
    dotenv_path = os.path.join(os.getcwd(), '.env')
    if os.path.exists(dotenv_path):
        with open(dotenv_path, 'r') as f:
            for line in f:
                if line.startswith('POLYTOPE_MASTER_KEY='):
                    return line.split('=')[1].strip().strip('"').strip("'")
    return "sovereign-development-key"

def simulate_telemetry(url, key, hr, hrv, stress, focus):
    endpoint = f"{url}/api/telemetry"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "hr": hr,
        "hrv": hrv,
        "stress_score": stress,
        "focus": focus,
        "valence": 0.5,
        "arousal": 0.5
    }
    
    print(f"[ Simulating ] HR: {hr}, HRV: {hrv}, Stress: {stress}, Focus: {focus}")
    
    try:
        # Note: In a real scenario we'd need to login first to get a JWT 
        # but for internal simulation we can mock/use the master key if the backend allows 
        # OR we can just assume the backend is in dev mode.
        # However, app.py uses verify_authenticated which checks JWT.
        # For simplicity in this sim, we'll try to login first if needed.
        
        login_resp = requests.post(f"{url}/auth/login", json={"key": key})
        if login_resp.status_code == 200:
            token = login_resp.json().get("access_token")
            headers["Authorization"] = f"Bearer {token}"
        else:
            print(f"[ ERROR ] Login failed: {login_resp.text}")
            return
            
        resp = requests.post(endpoint, headers=headers, json=payload)
        if resp.status_code == 200:
            result = resp.json()
            print(f"[ SUCCESS ] Flow Mode: {result['flow_state']['mode']} - {result['flow_state']['reason']}")
        else:
            print(f"[ FAILED ] Status {resp.status_code}: {resp.text}")
            
    except Exception as e:
        print(f"[ ERROR ] {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Alluci Telemetry Simulator")
    parser.add_argument("--url", default="http://localhost:8000", help="Backend URL")
    parser.add_argument("--key", default=get_auth_token(), help="Sovereign Master Key")
    parser.add_argument("--hr", type=int, default=72, help="Heart Rate")
    parser.add_argument("--hrv", type=int, default=50, help="Heart Rate Variability")
    parser.add_argument("--stress", type=float, default=20.0, help="Stress Score (0-100)")
    parser.add_argument("--focus", type=float, default=0.5, help="Focus Level (0.0-1.0)")
    parser.add_argument("--loop", action="store_true", help="Run in a loop")
    
    args = parser.parse_args()
    
    if args.loop:
        print("Starting telemetry loop. Press Ctrl+C to stop.")
        try:
            while True:
                simulate_telemetry(args.url, args.key, args.hr, args.hrv, args.stress, args.focus)
                time.sleep(5)
        except KeyboardInterrupt:
            print("\nStopped.")
    else:
        simulate_telemetry(args.url, args.key, args.hr, args.hrv, args.stress, args.focus)
