import json
import base64
import uuid
import random
from locust import HttpUser, task, between, events
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# We can import backend config to get the valid keys for testing
try:
    from backend.config import settings
    POLYTOPE_MASTER_KEY = settings.POLYTOPE_MASTER_KEY
except ImportError:
    # Fallback for isolated execution
    import os
    POLYTOPE_MASTER_KEY = os.getenv("POLYTOPE_MASTER_KEY", "dummy_master_key_for_testing")

# Generate a persistent Ed25519 keypair for the simulated user
private_key = ed25519.Ed25519PrivateKey.generate()
public_key = private_key.public_key()
public_key_hex = public_key.public_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PublicFormat.Raw
).hex()

def _canonicalize(obj) -> str:
    if obj is None or not isinstance(obj, (dict, list)):
        return json.dumps(obj, separators=(',', ':'))
    if isinstance(obj, list):
        return f"[{','.join(_canonicalize(x) for x in obj)}]"
    sorted_keys = sorted(obj.keys())
    parts = [f'"{k}":{_canonicalize(obj[k])}' for k in sorted_keys]
    return "{" + ",".join(parts) + "}"

def generate_manifest_header(objective: str, autonomy_level: str) -> str:
    """Generates the X-Execution-Manifest Ed25519 signed header."""
    manifest = {
        "rootPublicKey": public_key_hex,
        "autonomyLevel": autonomy_level,
        "objectiveId": str(uuid.uuid4()),
        "modelVersion": "load-test-v1",
        "plannerVersion": "load-test-v1",
        "payloadHash": ""  # Simplified
    }
    
    canonical_str = _canonicalize(manifest)
    signature = private_key.sign(canonical_str.encode("utf-8"))
    
    signed_payload = {
        "manifest": manifest,
        "signature": signature.hex()
    }
    
    return base64.b64encode(json.dumps(signed_payload).encode("utf-8")).decode("utf-8")


class AlluciAgentUser(HttpUser):
    # Wait between 1 and 3 seconds between tasks to simulate real user thinking
    wait_time = between(1, 3)

    def on_start(self):
        """Authenticate the user before any tasks run."""
        res = self.client.post("/api/v1/auth/login", json={"key": POLYTOPE_MASTER_KEY})
        if res.status_code != 200:
            print(f"Failed to authenticate: {res.text}")

    @task(1)
    def simulate_biometric_variance(self):
        """
        Simulate varying Affective Tension (PSI) by updating biometrics.
        This impacts the system's autonomic gating and routing.
        """
        # Randomize valence and arousal to fluctuate PSI
        valence = random.randint(0, 1024)
        arousal = random.randint(0, 1024)
        
        payload = {
            "hrv": random.randint(30, 100),
            "gsr": random.randint(100, 500),
            "valence": valence,
            "arousal": arousal
        }
        
        # NOTE: Using /channels/iwatch/biometrics endpoint
        self.client.post("/api/v1/channels/iwatch/biometrics", json=payload)

    @task(3)
    def execute_varying_objectives(self):
        """
        Simulate the primary LLM inference load with varying complexity.
        """
        # 1: Low complexity (Memory retrieval)
        # 2: Medium complexity (API synthesis)
        # 3: High complexity (Multi-agent orchestration / DAG generation)
        complexity_pool = [
            ("What is my schedule for today?", "SEMI_AUTONOMOUS"),
            ("Cross-reference my inbox with my Verus vault transactions.", "SEMI_AUTONOMOUS"),
            ("Analyze the network topology and formulate a polytopic DAG plan to optimize my server costs.", "SOVEREIGN")
        ]
        
        objective_text, autonomy = random.choice(complexity_pool)
        
        # Cryptographically sign the request
        manifest_header = generate_manifest_header(objective_text, autonomy)
        headers = {
            "X-Execution-Manifest": manifest_header
        }
        
        payload = {
            "objective": objective_text,
            "autonomy_level": autonomy
        }
        
        # Fire request to the Executive Objective endpoint
        with self.client.post("/api/v1/objective/execute", json=payload, headers=headers, catch_response=True) as response:
            # Add type ignores because IDEs (Pylance/MyPy) think response is requests.Response
            # but Locust returns a ResponseContextManager when catch_response=True
            if response.status_code in [200, 202]:
                response.success()  # type: ignore
            elif response.status_code == 403:
                # 403 can happen if the dynamic PSI blocked the AutonomyLevel! This is intended behavior.
                response.success()  # type: ignore
            else:
                response.failure(f"Unexpected status: {response.status_code}")  # type: ignore

    @task(2)
    def check_memory_store(self):
        """
        Simulate minor background interactions like memory storage.
        """
        payload = {
            "content": f"User interaction event {uuid.uuid4()}",
            "tags": ["load_test", "telemetry"],
            "importance": random.random()
        }
        self.client.post("/api/v1/memory/store", json=payload)
