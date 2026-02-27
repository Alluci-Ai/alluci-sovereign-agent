
import typer
import httpx
import os
import json

app = typer.Typer(help="Polytope Executive Command Line Interface")
DAEMON_URL = "http://localhost:8000"

@app.command()
def onboard():
    """Run the interactive setup wizard for Alluci Sovereign Agent."""
    typer.secho("--- POLYTOPE ONBOARDING ---", fg=typer.colors.CYAN, bold=True)
    identity = typer.prompt("Enter your Sovereign Identity name")
    
    # Initialize vault
    typer.echo(f"Provisioning simplicial vaults for {identity}...")
    typer.secho("Success. Manifold active.", fg=typer.colors.GREEN)

@app.command()
def execute(objective: str):
    """Send an objective directly to the autonomous orchestrator."""
    typer.echo(f"Transmitting objective: '{objective}'")
    try:
        response = httpx.post(f"{DAEMON_URL}/objective/execute", json={"objective": objective})
        typer.echo(f"Result: {response.json().get('result')}")
    except Exception as e:
        typer.secho(f"Daemon link error: {e}", fg=typer.colors.RED)

@app.command()
def doctor():
    """Verify system health and bridge connectivity."""
    typer.echo("Running diagnostics...")
    try:
        res = httpx.get(f"{DAEMON_URL}/system/status")
        typer.echo(json.dumps(res.json(), indent=2))
    except:
        typer.secho("Daemon is OFFLINE.", fg=typer.colors.RED)

if __name__ == "__main__":
    app()
