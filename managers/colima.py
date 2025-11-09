from utils.shell import ShellRunner, default_shell_runner
from utils.display import console

class ColimaManager:
    def __init__(self, shell: ShellRunner = default_shell_runner):
        self.shell = shell

    def check_and_start(self):
        console.print("\n[bold magenta]== 1. Checking Colima Status ==[/bold magenta]")
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