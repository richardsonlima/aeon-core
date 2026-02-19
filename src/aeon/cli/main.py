import typer
import os
import yaml
from rich.console import Console
from rich.panel import Panel
from aeon.core.config import AeonConfig, AgentConfig, ModelConfig, CapabilitiesConfig, ServerConfig

app = typer.Typer(
    name="aeon",
    help="Æon Framework CLI - Build, Run, and Manage Autonomous Agents",
    add_completion=False,
)
console = Console()

@app.command()
def init(
    name: str = typer.Argument(..., help="Name of the agent/project"),
    path: str = typer.Option(".", help="Directory to create the project in"),
    template: str = typer.Option("default", help="Project template (default, full, minimal)")
):
    """
    Initialize a new Æon Agent project with a configuration file.
    """
    project_dir = os.path.join(path, name)
    if os.path.exists(project_dir):
        console.print(f"[bold red]Error:[/bold red] Directory '{project_dir}' already exists.")
        raise typer.Exit(1)

    os.makedirs(project_dir)
    
    # Create aeon.yaml
    config = AeonConfig(
        agent=AgentConfig(
            name=name,
            model=ModelConfig(
                provider="ollama",
                name="mistral",
                base_url="http://localhost:11434"
            )
        ),
        capabilities=CapabilitiesConfig(
            browser={"enabled": True, "headless": True},
            memory={"enabled": True},
            automation={"enabled": False}
        ),
        server=ServerConfig(
            webhooks=True,
            port=8000
        )
    )
    
    config_path = os.path.join(project_dir, "aeon.yaml")
    with open(config_path, "w") as f:
        # Pydantic v2 model_dump with mode='json' turns Enums into strings
        yaml.dump(config.model_dump(mode='json'), f, default_flow_style=False, sort_keys=False)
        
    # Create simple tasks.py
    with open(os.path.join(project_dir, "tasks.py"), "w") as f:
        f.write("# Define your custom agent tasks here\n")
        f.write("from aeon.core.agent import Agent\n\n")
        f.write("async def startup_task(agent: Agent):\n")
        f.write("    await agent.speak('Hello! I am ready.')\n")

    console.print(Panel(f"[bold green]Created new project: {name}[/bold green]\n\nRun:\n  cd {project_dir}\n  aeon serve", title="Success"))

@app.command()
def serve(
    config: str = typer.Option("aeon.yaml", help="Path to configuration file"),
    port: int = typer.Option(None, help="Override port"),
    reload: bool = typer.Option(False, help="Enable auto-reload")
):
    """
    Start the Agent Gateway Server.
    """
    from aeon.runtime.gateway import GatewayServer
    from aeon.core.config import load_config
    import uvicorn

    if not os.path.exists(config):
        console.print(f"[bold red]Error:[/bold red] Config file '{config}' not found. Run 'aeon init' first.")
        raise typer.Exit(1)

    aeon_config = load_config(config)
    if port:
        aeon_config.server.port = port

    console.print(f"[bold blue]Starting Æon Gateway for agent: {aeon_config.agent.name}[/bold blue]")
    
    # We will use uvicorn to run the gateway app
    gateway = GatewayServer(aeon_config)
    uvicorn.run(gateway.app, host=aeon_config.server.host, port=aeon_config.server.port)

@app.command()
def run(
    input: str = typer.Argument(..., help="Input text for the agent"),
    config: str = typer.Option("aeon.yaml", help="Path to configuration file")
):
    """
    Run the agent once with a specific input.
    """
    import asyncio
    from aeon.core.config import load_config
    from aeon import Agent
    from aeon.tools.browser import BrowserTool
    from aeon.core.config import TrustLevel
    
    if not os.path.exists(config):
        console.print(f"[bold red]Error:[/bold red] Config file '{config}' not found.")
        raise typer.Exit(1)
        
    aeon_config = load_config(config)
    
    console.print(f"[bold green]Running Agent: {aeon_config.agent.name}[/bold green]")
    
    async def _run():
        tools = []
        if aeon_config.capabilities.browser.enabled:
            tools.append(BrowserTool(headless=aeon_config.capabilities.browser.headless))
            
        agent = Agent(
            name=aeon_config.agent.name,
            model=f"{aeon_config.agent.model.provider}/{aeon_config.agent.model.name}",
            protocols=[],
            trust_level=aeon_config.agent.trust_level
        )
        
        console.print(f"[dim]Input: {input}[/dim]")
        result = await agent.run(input)
        console.print(Panel(str(result), title="Agent Output"))
        
    asyncio.run(_run())

@app.command()
def doctor():
    """
    Check environment health and dependencies.
    """
    console.print("[bold]Checking Æon Environment...[/bold]")
    # Checks for: python version, pip dependencies, playwright, docker (optional)
    import sys
    console.print(f"Python: {sys.version.split()[0]} [green]OK[/green]")
    
    try:
        import playwright
        console.print("Playwright: Installed [green]OK[/green]")
    except ImportError:
        console.print("Playwright: [red]Not Installed[/red] (run 'pip install playwright && playwright install')")

if __name__ == "__main__":
    app()
