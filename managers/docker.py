from pathlib import Path
from utils.shell import ShellRunner, default_shell_runner
from utils.display import console
from utils.exceptions import ConfigError
from config import setting

class DockerManager:
    def __init__(self, shell: ShellRunner = default_shell_runner):
        self.shell = shell
        self.network_name = setting.DOCKER_EXTERNAL_NETWORK

    def ensure_network_exists(self):
        console.print("\n[bold magenta]== 2. Ensuring Docker Network Exists ==[/bold magenta]")
        if not self.network_name:
            raise ConfigError("DOCKER_EXTERNAL_NETWORK is not defined in .env file.")
        
        network_exists_cmd = [
            "docker", "network", "ls",
            "--filter", f"name=^{self.network_name}$",
            "--format", "{{.Name}}"
        ]
        _, existing_network, _ = self.shell.run(network_exists_cmd)

        if existing_network == self.network_name:
            console.print(f"[green] Network '{self.network_name}' already exists.[/green]")
        else:
            console.print(f"[yellow] Network '{self.network_name}' not found. Creating it... [/yellow]")
            self.shell.run(["docker", "network", "create", self.network_name])
            console.print(f"[green] Network '{self.network_name}' created successfully [/green]")

    def compose_up(self, service_path: Path):
        self.shell.run(["docker", "compose", "up", "-d"], cwd=str(service_path))

    def compose_down(self, service_path: Path):
        self.shell.run(["docker", "compose", "down"], cwd=str(service_path))

    def compose_ps(self, service_path: Path):
        self.shell.run(["docker", "compose", "ps"], cwd=str(service_path))