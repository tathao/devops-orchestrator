from typing_extensions import Annotated

import typer

from utils.display import console
from utils.exceptions import OrchestratorException

from utils.shell import ShellRunner
from managers.colima import ColimaManager
from managers.docker import DockerManager
from managers.service import ServiceManager
from managers.vault import VaultManager
from managers.creator import ServiceCreator

app = typer.Typer()

try:
    shell_runner = ShellRunner(console)
    colima_manager = ColimaManager(shell_runner)
    docker_manager = DockerManager(shell_runner)
    service_manager = ServiceManager(docker_manager)
    vault_manager = VaultManager(shell_runner, docker_manager)
    service_creator = ServiceCreator(vault_manager)

except Exception as e:
    console.print(f"[bold red] Failed to initialize application managers: {e} [/bold red]")
    raise typer.Exit(code=2)

def run_pre_flight_checks():
    colima_manager.check_and_start()
    docker_manager.ensure_network_exists()

@app.command()
def start(service_name: Annotated[str, typer.Argument(help="Service name to start (eg: Mysql)")]):
    try:
        run_pre_flight_checks()
        service_manager.start(service_name)
    except OrchestratorException as e:
        console.print(f"[bold red] Error starting service: {e} [/bold red]")
        raise typer.Exit(code=1)
    
@app.command()
def stop(service_name: Annotated[str, typer.Argument(help="Service name to stop (eg: Mysql)")]):
    try:
        run_pre_flight_checks() 
        service_manager.stop(service_name)
    except OrchestratorException as e:
        console.print(f"[bold red] Error stopping service: {e} [/bold red]")
        raise typer.Exit(code=1)
    
@app.command()
def create(
    template_name: Annotated[str, typer.Option("--template", "-t", help="Template name in 'templates' folder.")],
    new_service_name: Annotated[str, typer.Option("--name", "-n", help="New service name to be created")]
):
    try:
        service_creator.create_service(template_name, new_service_name)
    except OrchestratorException as e:
        console.print(f"[bold red] Error creating service: {e} [/bold red]")
        raise typer.Exit(code=1)
    
@app.command("vault-setup")
def setup_vault():
    try:
        run_pre_flight_checks()
        vault_manager.setup()
    except OrchestratorException as e:
        console.print(f"[bold red] Error during Vault setup: {e} [/bold red]")
        raise typer.Exit(code=1)
    
if __name__ == "__main__":
    app()