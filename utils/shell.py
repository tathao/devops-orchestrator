import subprocess
from rich.console import Console
from .exceptions import CommandError
from .display import console

class ShellRunner:
    def __init__(self, console: Console = console):
        self.console = console

    def run(
        self,
        command: list[str],
        cwd: str = None,
        exit_on_error: bool = True
    ) -> tuple[bool, str, str]:
        self.console.print(f"[bold cyan] Executing: {' '.join(command)}[/bold cyan]")
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=exit_on_error,
                cwd=cwd
            )

            return True, result.stdout.strip(), result.stderr.strip()
        except subprocess.CalledProcessError as e:
            if exit_on_error:
                self.console.print(f"[bold red] Error running command: {' '.join(command)}[/bold red]")
                self.console.print(f"[red]   STDOUT: {e.stdout}[/red]")
                self.console.print(f"[red]   STDERR: {e.stderr}[/red]")
                raise CommandError(
                    message=f"Command failed: {' '.join(command)}",
                    stdout=e.stdout.strip(),
                    stderr=e.stderr.strip()
                )
            return False, e.stdout.strip(), e.stderr.strip()
        except FileNotFoundError:
            self.console.print(f"[bold red] Command not found: {command[0]}. Is it installed and in your PATH? [/bold red]")
            raise CommandError(
                message=f"Command not found: {command[0]}",
                stdout="",
                stderr="Command not found"
            )
        

default_shell_runner = ShellRunner(console=console)