from typing_extensions import Annotated

import typer
import time
from utils.display import console
from utils.exceptions import OrchestratorException

from utils.shell import ShellRunner
from managers.colima import ColimaManager
from managers.docker import DockerManager
from managers.service import ServiceManager
from managers.vault import VaultManager
from managers.creator import ServiceCreator

from managers.docker_inspector import DockerSDKRepository, TableRenderer, ContainerService


app = typer.Typer()

# ============================================================
#   STEP 1: Initialize base managers that don't need Docker
# ============================================================

try:
    shell_runner = ShellRunner(console)
    colima_manager = ColimaManager(shell_runner)
except Exception as e:
    console.print(f"[bold red] Failed to initialize Colima manager: {e} [/bold red]")
    raise typer.Exit(code=2)

# ============================================================
#   STEP 2: Lazy init (safe) for Docker-dependent managers
# ============================================================
def run_pre_flight_checks() -> dict:

    # 1️⃣ Start Colima
    colima_manager.check_and_start()

    # 2️⃣ DockerManager init & ensure network
    docker_manager = DockerManager(shell_runner)

    max_retries = 5
    for i in range(max_retries):
        try:
            docker_manager.ensure_network_exists()
            break
        except Exception as e:
            if i < max_retries - 1:
                console.print(f"[yellow]⚠️ Network not ready, retrying ({i+1}/{max_retries})...[/yellow]")
                time.sleep(2)
            else:
                raise OrchestratorException(f"Failed to ensure Docker network: {e}")
            
    # 4️⃣ Other managers
    service_manager = ServiceManager(docker_manager)
    vault_manager = VaultManager(shell_runner, docker_manager)
    service_creator = ServiceCreator(vault_manager)

    # 5️⃣ Container service
    container_repo = DockerSDKRepository()
    container_renderer = TableRenderer()
    container_service = ContainerService(container_repo, container_renderer)

    return {
        "docker_manager": docker_manager,
        "service_manager": service_manager,
        "vault_manager": vault_manager,
        "service_creator": service_creator,
        "container_service": container_service,
    }

@app.command()
def start(service_name: Annotated[str, typer.Argument(help="Service name to start (eg: Mysql)")]):
    mgrs = run_pre_flight_checks()
    try:
        mgrs["service_manager"].start(service_name)
    except OrchestratorException as e:
        console.print(f"[bold red] Error starting service: {e} [/bold red]")
        raise typer.Exit(code=1)
    
@app.command()
def stop(service_name: Annotated[str, typer.Argument(help="Service name to stop (eg: Mysql)")]):
    mgrs = run_pre_flight_checks()
    try:
        mgrs["service_manager"].stop(service_name)
    except OrchestratorException as e:
        console.print(f"[bold red] Error stopping service: {e} [/bold red]")
        raise typer.Exit(code=1)
    
@app.command()
def create(
    template_name: Annotated[str, typer.Option("--template", "-t", help="Template name in 'templates' folder.")],
    new_service_name: Annotated[str, typer.Option("--name", "-n", help="New service name to be created")]
):
    mgrs = run_pre_flight_checks()
    try:
        mgrs["service_creator"].create_service(template_name, new_service_name)
    except OrchestratorException as e:
        console.print(f"[bold red] Error creating service: {e} [/bold red]")
        raise typer.Exit(code=1)
    
@app.command("vault-setup")
def setup_vault():
    mgrs = run_pre_flight_checks()
    try:
        mgrs["vault_manager"].setup()
    except OrchestratorException as e:
        console.print(f"[bold red] Error during Vault setup: {e} [/bold red]")
        raise typer.Exit(code=1)
    

@app.command("containers")
def list_containers(
    all: Annotated[bool, typer.Option("--all", "-a", help="Show all containers (including stopped)")] = False
):
    mgrs = run_pre_flight_checks()
    try:
        mgrs["container_service"].list_and_render_containers(include_all=all)
    except OrchestratorException as e:
        console.print(f"[bold red] Error listing containers: {e} [/bold red]")
        raise typer.Exit(code=1)
    
if __name__ == "__main__":
    app()
