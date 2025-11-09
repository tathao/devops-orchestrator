import hvac
import time
import re
import json
from rich.status import Status

from config import setting
from utils.display import console
from utils.shell import ShellRunner, default_shell_runner
from utils.security import get_vault_token_from_keyring, set_vault_token_in_keyring
from managers.docker import DockerManager
from utils.exceptions import VaultError, CommandError

class VaultManager:
    def __init__(self, shell: ShellRunner, docker: DockerManager):
        self.shell = shell
        self.docker = docker
        self.client = None

    def get_client(self) -> hvac.Client:
        if self.client and self.client.is_authenticated():
            return self.client
        try:
            token = get_vault_token_from_keyring()
        except VaultError as e:
            console.print(f"[bold red] {e} [/bold red]")
            raise

        client = hvac.Client(url=setting.VAULT_ADDR, token=token)

        if not client.is_authenticated():
            raise VaultError("Vault authentication failed. Is Vault unsealed? Is the token valid?")
        
        self.client = client
        return self.client
    
    def store_secrets(self, secret_path: str, secret_data: dict):
        try:
            client = self.get_client()
            clean_path = secret_path.replace("secret/data/", "")
            client.secrets.kv.v2.create_or_update_secret(path=clean_path, secret=secret_data)
            console.print(f"    -> Secrets stored in Vault at [green]secret/data/{clean_path}[/green]")
        except Exception as e:
            raise VaultError(f"Failed to store secrets at {secret_path}: {e}")
        
    def setup(self):
        self._start_container()
        self._wait_for_ready()

        keys_data = self._initialize_or_load_keys()

        self._unseal(keys_data)

        root_token = keys_data["root_token"]
        self.client = hvac.Client(url=setting.VAULT_ADDR, token=root_token)

        self._enable_kv_engine()
        self._store_root_token_in_keyring(root_token)
        self._print_summary(root_token)

    def _start_container(self):
        console.print("\n[bold magenta]== 3. Starting Vault Container ==[/bold magenta]")
        self.docker.compose_up(setting.VAULT_SERVICE_DIR)

    def _wait_for_ready(self):
        console.print("\n[bold magenta]== 4. Waiting for Vault to be ready == [/bold magenta]")
        with Status("[yellow] Pinging Vault...", console=console) as status:
            for i in range(15):
                time.sleep(3)
                status.update(f"[yellow] Pinging Vault...(attempt {i+1}/15)[/yellow]")
                success, stdout, _ = self.shell.run(
                    ["docker", "exec", setting.VAULT_CONTAINER_NAME, "vault", "status", "-address", setting.VAULT_ADDR],
                    exit_on_error=False
                )
                if stdout or success:
                    console.print("[green] Vault container is responsive [/green]")
                    return
        raise VaultError("Vault did not become healthy in time.")
    
    def _initialize_or_load_keys(self) -> dict:
        console.print("\n[bold magenta]== 5. Checking Vault Initialization Status == [/bold magenta]")
        _, status_output, _ = self.shell.run(["docker", "exec", setting.VAULT_CONTAINER_NAME, "vault", "status"], exit_on_error=False)

        if re.search(r"Initialized\s+true", status_output):
            console.print("[green] Vault is already initialized. Loading keys... [/green]")
            if not setting.VAULT_KEYS_FILE.exists():
                raise VaultError(f"Vault key file '{setting.VAULT_KEYS_FILE}' not found. Cannot unseal.")
            with open(setting.VAULT_KEYS_FILE, "r") as f:
                return json.load(f)
        
        console.print("[yellow] Vault is not initialized. Initializing now... [/yellow]")
        _, init_output, _ = self.shell.run([
            "docker", "exec", setting.VAULT_CONTAINER_NAME, "vault", "operator", "init",
            "-key-shares=5", "-key-threshold=3", "-format=json"
        ])
        with open(setting.VAULT_KEYS_FILE, "w") as f:
            f.write(init_output)
        console.print(f"[green] Vault initialized. Keys and root token saved to '{setting.VAULT_KEYS_FILE}' [/green]")
        return json.loads(init_output)
    
    def _unseal(self, key_data: dict):
        console.print("\n[bold magenta]== 6. Unsealing Vault ==[/bold magenta]")
        _, status_output, _ = self.shell.run(["docker", "exec", setting.VAULT_CONTAINER_NAME, "vault", "status"], exit_on_error=False)
        
        if re.search(r"Sealed\s+false", status_output):
            console.print("[green] Vault is already unsealed [/green]")
            return

        unseal_keys = key_data["unseal_keys_b64"][:3]
        console.print(f"Using {len(unseal_keys)} keys to unseal...")
        for key in unseal_keys:
            self.shell.run(["docker", "exec", setting.VAULT_CONTAINER_NAME, "vault", "operator", "unseal", key])
        console.print("[green] Vault unseal successfully [/green]")

    def _enable_kv_engine(self):
        console.print("\n[bold magenta]== 6.1. Checking KV Secrets Engine ==[/bold magenta]")
        if not self.client:
             raise VaultError("Vault client not initialized for enabling KV engine.")

        mounts = self.client.sys.list_mounted_secrets_engines().get("data", {})
        if "secret/" not in mounts:
            console.print("[yellow]KV v2 secrets engine not found at 'secret/'. Enabling it...[/yellow]")
            self.client.sys.enable_secrets_engine(
                backend_type="kv",
                path="secret",
                options={"version": "2"}
            )
            console.print("[green]KV v2 secrets engine enabled at path 'secret/'[/green]")
        else:
            console.print("[green]KV v2 secrets engine already enabled at 'secret/'[/green]")

    def _store_root_token_in_keyring(self, root_token: str):
        set_vault_token_in_keyring(root_token)
        console.print(f"[bold green] -> Root token has been automatically saved to your system's KeyChain [/bold green]")

    def _print_summary(self, root_token: str):
        console.print("\n[bold magenta]== 7. Vault Setup Completed == [/bold magenta]")
        console.print(f"[bold] Root Token: [/bold] {root_token}")
        console.print(f"[bold] Keys stored in: [/bold] {setting.VAULT_KEYS_FILE}")
        console.print("\n[yellow] For command-line access, run these commands in your shell: [/yellow]")
        console.print(f"    [bold] export VAULT_ADDR='{setting.VAULT_ADDR}' [/bold]")
        console.print(f"    [bold] export VAULT_TOKEN='{root_token}' [/bold]")
        console.print(f"[bold] Vault UI: [/bold] {setting.VAULT_ADDR}")