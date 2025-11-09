from pathlib import Path
from utils.display import console
from utils.exceptions import ServiceNotFound
from managers.docker import DockerManager
from config import setting

class ServiceManager:
    def __init__(self, docker_manager: DockerManager):
        self.docker = docker_manager
        self.service_root = setting.SERVICE_DIR

    def _get_service_path(self, service_name: str) -> Path:
        service_dir = self.service_root / service_name
        compose_file = service_dir / "docker-compose.yml"

        if not service_dir.is_dir() or not compose_file.exists():
            msg = f"Service '{service_name}' not found."
            console.print(f"[bold red] {msg} [/bold red]")
            console.print(f"   Directory '{service_dir}' or file '{compose_file}' does not exist.")
            raise ServiceNotFound(msg)
        return service_dir
    
    def start(self, service_name: str):
        console.print(f"\n[bold magenta]== 8. Starting Service: {service_name} == [/bold magenta]")
        service_dir = self._get_service_path(service_name)

        self.docker.compose_up(service_dir)
        console.print(f"[bold green] Service '{service_name}' started successfully! [/bold green]")
        self.docker.compose_ps(service_dir)

    def stop(self, service_name: str):
        console.print(f"\n[bold magenta]== 9. Stopping Service: {service_name} == [/bold magenta]")
        service_dir = self._get_service_path(service_name)

        self.docker.compose_down(service_dir)
        console.print(f"[bold green] Service '{service_name}' stopped successfully! [/bold green]")