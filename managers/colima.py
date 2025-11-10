import os
import time
from utils.shell import ShellRunner, default_shell_runner
from utils.display import console

class ColimaManager:
    def __init__(self, shell: ShellRunner = default_shell_runner):
        self.shell = shell
        self.colima_socket = f"unix://{os.path.expanduser('~')}/.colima/docker.sock"
        self.default_socket = "unix:///var/run/docker.sock"

    def check_and_start(self, retry_seconds: int = 10):
        console.print("\n[bold magenta]== 1. Checking Colima/Docker Status ==[/bold magenta]")

        if self._is_docker_socket_available(self.default_socket):
            os.environ["DOCKER_HOST"] = self.default_socket
            console.print("[green]✅ Docker Desktop socket is available.[/green]")
            return
        
        if self._is_docker_socket_available(self.colima_socket):
            os.environ["DOCKER_HOST"] = self.colima_socket
            console.print("[green]✅ Colima socket is available.[/green]")
            return
        
        console.print("[yellow]⚠️ Neither Docker Desktop nor Colima socket found. Checking Colima...[/yellow]")

        if not self._is_colima_installed():
            raise RuntimeError(
                "[red]❌ Colima is not installed. Please install it first via: brew install colima[/red]"
            )

        try:
            success, stdout, _ = self.shell.run(["colima", "status"], exit_on_error=False)
            if success and "Running" in stdout:
                console.print("[green] Colima is running. [/green]")
            else:
                console.print("[yellow] Colima is not running. Starting it now... [/yellow]")
                self.shell.run(["colima", "start"])
                console.print("[green]Colima started successfully.[/green]")
        except Exception:
            console.print("[yellow]Could not determine Colima status. Assuming it needs to be started.[/yellow]")
            self.shell.run(["colima", "start"])
            console.print("[green]Colima started successfully.[/green]")

        if self._is_docker_socket_available(self.colima_socket):
            os.environ["DOCKER_HOST"] = self.colima_socket
            console.print("[green]🐳 Docker socket via Colima is ready.[/green]")
        else:
            raise RuntimeError(
                "[red]❌ Docker socket via Colima is not available after starting Colima.[/red]"
            )
        
        socket_path = self.colima_socket.replace("unix://", "")
        for _ in range(retry_seconds):
            if os.path.exists(socket_path):
                os.environ["DOCKER_HOST"] = self.colima_socket
                console.print("[green]🐳 Docker socket via Colima is ready.[/green]")
                return
            time.sleep(1)

        raise RuntimeError("[red]❌ Docker socket did not appear after starting Colima[/red]")

        
    def _is_colima_installed(self) -> bool:
        success, stdout, _ = self.shell.run(["command", "-v", "colima"], exit_on_error=False)
        return success and bool(stdout.strip())
    
    def _is_docker_socket_available(self, socket_path: str) -> bool:
        if socket_path.startswith("unix://"):
            path = socket_path.replace("unix://", "")
            return os.path.exists(path)
        return False