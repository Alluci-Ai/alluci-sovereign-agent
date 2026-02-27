
import typer
import httpx
import os

app = typer.Typer()
API_URL = "http://localhost:8000"

@app.command()
def onboard():
    """Run the interactive setup wizard for Alluci Sovereign Agent."""
    typer.echo("[ POLYTOPE ]: Initializing onboarding manifold...")
    name = typer.prompt("What is your sovereign identity name?")
    typer.echo(f"Welcome, {name}. Configuring Simplicial Vaults...")

@app.command()
def execute(objective: str):
    """Send a command directly to the running Polytope daemon."""
    response = httpx.post(f"{API_URL}/objective/execute", json={"objective": objective})
    typer.echo(response.json().get("result", "Communication error."))

@app.command()
def doctor():
    """Run system diagnostics on the local manifold."""
    typer.echo("[ DIAGNOSTICS ]: Checking daemon status...")
    try:
        res = httpx.get(f"{API_URL}/system/status")
        typer.echo(f"Daemon Online: {res.json()}")
    except:
        typer.echo("Daemon OFFLINE. Start with 'python -m backend.main'")

if __name__ == "__main__":
    app()
