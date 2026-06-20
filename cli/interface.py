import typer
import httpx
import json
import base64
import uuid
import os
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

app = typer.Typer(help="Polytope Executive Command Line Interface")
DAEMON_URL = "http://localhost:8000"

class IdentityManager:
    def __init__(self):
        self.key_dir = Path.home() / ".alluci" / "keys"
        self.key_path = self.key_dir / "id_ed25519"
        self.private_key = None
        self.public_key_hex = None

    def load_or_generate(self):
        if not self.key_path.exists():
            self.key_dir.mkdir(parents=True, exist_ok=True)
            self.private_key = ed25519.Ed25519PrivateKey.generate()
            pem = self.private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            self.key_path.write_bytes(pem)
            self.key_path.chmod(0o600)
        else:
            pem = self.key_path.read_bytes()
            self.private_key = serialization.load_pem_private_key(pem, password=None)
        
        public_key = self.private_key.public_key()
        self.public_key_hex = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        ).hex()

def _canonicalize(obj) -> str:
    if obj is None or not isinstance(obj, (dict, list)):
        return json.dumps(obj, separators=(',', ':'), ensure_ascii=False)
    if isinstance(obj, list):
        return f"[{','.join(_canonicalize(x) for x in obj)}]"
    sorted_keys = sorted(obj.keys())
    parts = [f'"{k}":{_canonicalize(obj[k])}' for k in sorted_keys]
    return "{" + ",".join(parts) + "}"

def generate_manifest_header(identity: IdentityManager, objective: str, autonomy_level: str) -> str:
    manifest = {
        "rootPublicKey": identity.public_key_hex,
        "autonomyLevel": autonomy_level,
        "objectiveId": str(uuid.uuid4()),
        "modelVersion": "cli-v1",
        "plannerVersion": "cli-v1",
        "payloadHash": ""  # Simplified for CLI
    }
    
    canonical_str = _canonicalize(manifest)
    signature = identity.private_key.sign(canonical_str.encode("utf-8"))
    
    signed_payload = {
        "manifest": manifest,
        "signature": signature.hex()
    }
    
    return base64.b64encode(json.dumps(signed_payload).encode("utf-8")).decode("utf-8")

@app.command()
def onboard():
    """Run the interactive setup wizard for Alluci Sovereign Agent."""
    typer.secho("--- POLYTOPE ONBOARDING ---", fg=typer.colors.CYAN, bold=True)
    identity = typer.prompt("Enter your Sovereign Identity name")
    
    # Initialize vault
    typer.echo(f"Provisioning simplicial vaults for {identity}...")
    
    # Setup keys
    id_mgr = IdentityManager()
    id_mgr.load_or_generate()
    typer.echo(f"Generated Ed25519 root keypair: {id_mgr.public_key_hex[:16]}...")
    
    typer.secho("Success. Manifold active.", fg=typer.colors.GREEN)

@app.command()
def execute(objective: str):
    """Send an objective directly to the autonomous orchestrator."""
    typer.echo(f"Transmitting objective: '{objective}'")
    try:
        identity = IdentityManager()
        identity.load_or_generate()
        
        autonomy_level = "SEMI_AUTONOMOUS"
        manifest_header = generate_manifest_header(identity, objective, autonomy_level)
        
        headers = {
            "X-Execution-Manifest": manifest_header
        }
        payload = {"objective": objective, "autonomy_level": autonomy_level}
        
        response = httpx.post(f"{DAEMON_URL}/api/v1/objective/execute", json=payload, headers=headers)
        
        if response.status_code in [200, 202]:
            typer.echo(f"Result: {response.json()}")
        else:
            typer.secho(f"Execution rejected: {response.status_code} - {response.text}", fg=typer.colors.RED)
    except Exception as e:
        typer.secho(f"Daemon link error: {e}", fg=typer.colors.RED)

@app.command()
def doctor():
    """Verify system health and bridge connectivity."""
    typer.echo("Running diagnostics...")
    try:
        res = httpx.get(f"{DAEMON_URL}/api/v1/system/status")
        typer.echo(json.dumps(res.json(), indent=2))
    except Exception:
        typer.secho("Daemon is OFFLINE.", fg=typer.colors.RED)

if __name__ == "__main__":
    app()
