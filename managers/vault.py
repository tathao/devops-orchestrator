"""
VaultManager v2.0
Clean, production-oriented Vault manager for orchestrator CLI.

Goals / features:
- Clear separation between addresses used from host (for hvac/requests) vs container-local CLI
- Robust, JSON-based status checks using HTTP /v1/sys/health and `vault status -format=json` when needed
- Idempotent initialization (won't re-init if Vault already initialized)
- Robust unseal with per-key verification and backoff
- Atomic saving of init keys/root token (file permissions 0o600)
- Saving root token to OS keyring via existing helper
- Minimal external side-effects (DockerManager used only to start container)
- Good logging with rich.console

Assumptions (these names should exist in your repo):
- `setting.VAULT_ADDR` (host address, e.g. "http://127.0.0.1:8200")
- `setting.VAULT_ADDR_CONTAINER` (container-local address, e.g. "http://127.0.0.1:8200")
- `setting.VAULT_CONTAINER_NAME` (docker service/container name)
- `setting.VAULT_SERVICE_DIR` (path used by DockerManager.compose_up)
- `setting.VAULT_KEYS_FILE` (pathlib.Path where to store init JSON)
- `ShellRunner` interface with .run(cmd: List[str], exit_on_error: bool=True) -> (success: bool, stdout: str, stderr: str)
- `DockerManager` interface with .compose_up(directory: str)
- `set_vault_token_in_keyring(token: str)` available
- `VaultError` exception type

If your project uses slightly different names, adapt imports/setting names accordingly.
"""

from __future__ import annotations

import json
import os
import stat
import tempfile
import time
from pathlib import Path
from typing import Dict, Optional, Tuple, List

import hvac
import requests
from rich.console import Console
from rich.status import Status

# Project-specific imports (adjust if your layout differs)
from config import setting
from utils.shell import ShellRunner
from managers.docker import DockerManager
from utils.security import set_vault_token_in_keyring, get_vault_token_from_keyring
from utils.exceptions import VaultError

console = Console()


class VaultManager:
    """
    Robust Vault manager.

    Usage pattern:
    vm = VaultManager(shell=default_shell_runner, docker=docker_mgr)
    vm.setup() # idempotent: will start container, wait, init/unseal if needed, enable KV

    Important design points:
    - Uses HTTP health endpoint to determine readiness.
    - Uses container-local CLI for operations that are easier with `vault` binary (init/unseal)
    but uses host HTTP (hvac) for enabling engines and queries.
    """

    def __init__(
        self,
        shell: ShellRunner,
        docker: DockerManager,
        *,
        addr_host: Optional[str] = None,
        addr_container: Optional[str] = None,
        container_name: Optional[str] = None,
        keys_file: Optional[Path] = None,
        max_wait_seconds: int = 90,
        health_interval: float = 3.0,
    ):
        self.shell = shell
        self.docker = docker
        self.addr_host = addr_host or getattr(
            setting, "VAULT_ADDR", "http://127.0.0.1:8200"
        )
        self.addr_container = addr_container or getattr(
            setting, "VAULT_ADDR_CONTAINER", "http://127.0.0.1:8200"
        )
        self.container_name = container_name or getattr(
            setting, "VAULT_CONTAINER_NAME", "vault"
        )
        self.keys_file = keys_file or getattr(
            setting, "VAULT_KEYS_FILE", Path("./vault_keys.json")
        )
        self.max_wait_seconds = max_wait_seconds
        self.health_interval = health_interval
        self.client: Optional[hvac.Client] = None

    # ------------------ Helper utilities ------------------
    def _http_health(self) -> Tuple[bool, Optional[Dict]]:
        """Call the Vault HTTP health endpoint at /v1/sys/health.

        Returns (ok, parsed_json_or_none).
        ok True means the endpoint returned a recognizable health response (any of 200/429/472/473/501 still informative).
        """
        url = self.addr_host.rstrip("/") + "/v1/sys/health"
        try:
            resp = requests.get(url, timeout=2)
        except Exception as exc:
            return False, None

        # Some responses are 200 (initialized/unsealed), 501 (not initialized), 429/472/473 (sealed / standby)
        if resp.status_code in (200, 429, 472, 473, 501):
            try:
                payload = resp.json()
            except Exception:
                payload = None
            return True, payload
        return False, None

    def _write_keys_file_atomic(self, data: str) -> None:
        # atomic write with secure permissions
        target = Path(self.keys_file)
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(prefix=target.name, dir=str(target.parent))
        try:
            with os.fdopen(fd, "w") as f:
                f.write(data)
            # set permissions to owner read/write only
            os.chmod(tmp_path, stat.S_IRUSR | stat.S_IWUSR)
            os.replace(tmp_path, str(target))
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # -------------------------------------------------------------------------
    #  AppRole Setup
    # -------------------------------------------------------------------------
    def enable_approle_auth(self):
        """
        Enable AppRole authentication method if not enabled.
        """
        self.ensure_client_authenticated()

        try:
            auths = self.client.sys.list_auth_methods().get("data", {})
            if "approle/" in auths:
                console.print("[green]AppRole auth method already enabled.[/green]")
                return
            
            self.client.sys.enable_auth_method(
                method_type="approle",
                path="approle"
            )
            console.print("[green]Enabled AppRole auth method.[/green]")
        except Exception as e:
            raise VaultError(f"Failed to enable AppRole auth method: {e}")
        
    def create_approle(self, role_name: str, policies: list[str], token_ttl="1h"):
        """
        Create an AppRole and attach policies.
        Example policies: ["default", "my-app-policy"]
        """
        self.ensure_client_authenticated()

        try:
            self.client.write(
                f"auth/approle/role/{role_name}",
                token_ttl=token_ttl,
                policies=",".join(policies)
            )
            console.print(f"[green]AppRole '{role_name}' created with policies: {policies}[/green]")
        except Exception as e:
            raise VaultError(f"Failed to create AppRole '{role_name}': {e}")
        
    def get_approle_credentials(self, role_name: str) -> dict:
        """
        Returns: {"role_id": "...", "secret_id": "..."}
        """
        self.ensure_client_authenticated()
        try:
            # Role ID
            role_id_resp = self.client.read(f"auth/approle/role/{role_name}/role-id")
            role_id = role_id_resp["data"]["role_id"]

            # Secret ID
            secret_id_resp = self.client.write(f"auth/approle/role/{role_name}/secret-id")
            secret_id = secret_id_resp["data"]["secret_id"]

            console.print(f"[green]Generated RoleID & SecretID for AppRole '{role_name}'[/green]")

            return {
                "role_id": role_id,
                "secret_id": secret_id
            }
        except Exception as e:
            raise VaultError(f"Failed to get credentials for AppRole '{role_name}': {e}")
        
    def ensure_client_authenticated(self):
        """
        Ensures that self.client exists and is authenticated.
        If not, attempts to re-auth using stored root token.
        """
        if self.client and self.client.is_authenticated():
            return
        
        from utils.security import get_vault_token_from_keyring
        
        try:
            token = get_vault_token_from_keyring()
        except Exception as exc:
            raise VaultError(f"Could not obtain Vault token from keyring: {exc}")
        
        self.client = hvac.Client(
            url=setting.VAULT_ADDR,
            token=token
        )

        if not self.client.is_authenticated():
            raise VaultError("Vault client is not authenticated — token may be invalid or Vault may be sealed.")
        
    def setup_approle(self, role_name: str, policies: list[str], save_to: str | None = None) -> dict:
        """
        Full AppRole setup:
        Enable -> Create role -> Generate credentials -> Optionally save to file.
        """
        console.print(f"[magenta]Setting up AppRole '{role_name}'...[/magenta]")
        self.enable_approle_auth()
        self.create_approle(role_name, policies)
        creds = self.get_approle_credentials(role_name)

        if save_to:
            with open(save_to, "w") as f:
                json.dump(creds, f, indent=2)
            console.print(f"[green]Saved AppRole credentials to {save_to}[/green]")
        
        console.print("[green]AppRole setup completed.[/green]")
        return creds

    # ------------------ High level operations ------------------
    def setup(self, *, compose_dir: Optional[str] = None) -> None:
        """Idempotent setup: start container -> wait -> init (if needed) -> unseal -> enable kv v2 -> store token."""
        console.print(
            "\n[bold magenta]== VaultManager v2.0 Setup Starting ==[/bold magenta]"
        )
        self._start_container(compose_dir)
        self._wait_for_ready()
        keys = self._initialize_or_load_keys()
        self._unseal(keys)
        # after unseal, create hvac client from host pointing to addr_host
        root_token = keys["root_token"]
        self.client = hvac.Client(url=self.addr_host, token=root_token)
        if not self.client.is_authenticated():
            raise VaultError(
                "hvac client could not authenticate with root token after unseal"
            )
        self._ensure_kv_v2()
        set_vault_token_in_keyring(root_token)
        self._print_summary(root_token)

    def full_setup_with_approle(
        self,
        role_name: str,
        policies: list[str],
        save_to: str | None = None
    ):
        """
        Full Vault setup pipeline + AppRole setup.
        """

        # 1) Start + Health + Init + Unseal
        self.setup()

        # 2) AppRole
        console.print("\n[bold magenta]== 8. Setting Up AppRole ==[/bold magenta]")
        creds = self.setup_approle(
            role_name=role_name,
            policies=policies,
            save_to=save_to
        )
        console.print("\n[bold green]Vault + AppRole setup completed successfully.[/bold green]")
        return creds

    def _start_container(self, compose_dir: Optional[str] = None) -> None:
        console.print("\n[bold magenta]== Starting Vault container ==[/bold magenta]")
        if compose_dir is None:
            compose_dir = getattr(setting, "VAULT_SERVICE_DIR", None)
        if not compose_dir:
            raise VaultError(
                "compose directory for Vault not provided and not found in settings"
            )
        self.docker.compose_up(compose_dir)

    def _wait_for_ready(self) -> None:
        console.print(
            "\n[bold magenta]== Waiting for Vault HTTP endpoint to respond ==[/bold magenta]"
        )
        deadline = time.time() + self.max_wait_seconds
        with Status("Pinging Vault HTTP health...") as status:
            while time.time() < deadline:
                status.update("Pinging Vault HTTP health endpoint...")
                ok, payload = self._http_health()
                if ok and payload is not None:
                    # reachable: payload contains keys like 'initialized' and 'sealed'
                    console.print("[green]Vault HTTP endpoint responded[/green]")
                    return
                time.sleep(self.health_interval)
            raise VaultError(
                "Vault HTTP health endpoint did not become responsive in time"
            )

    def _initialize_or_load_keys(self) -> Dict:
        console.print(
            "\n[bold magenta]== Checking Vault initialization status ==[/bold magenta]"
        )
        # Prefer HTTP JSON via host
        ok, payload = self._http_health()
        if ok and payload is not None and payload.get("initialized") is True:
            console.print(
                "[green]Vault reports initialized. Loading keys from file.[/green]"
            )
            if not self.keys_file.exists():
                raise VaultError(
                    f"Vault is initialized but keys file '{self.keys_file}' is missing"
                )
            with open(self.keys_file, "r") as f:
                return json.load(f)

        # Not initialized -> run container-local `vault operator init -format=json`
        console.print("[yellow]Vault is not initialized. Running init...[/yellow]")
        cmd = [
            "docker",
            "exec",
            self.container_name,
            "vault",
            "operator",
            "init",
            "-key-shares=5",
            "-key-threshold=3",
            "-format=json",
        ]
        success, stdout, stderr = self.shell.run(cmd, exit_on_error=False)
        if not success or not stdout:
            raise VaultError(
                f"Vault initialization failed: success={success} stderr={stderr}"
            )
        # Save keys securely
        try:
            parsed = json.loads(stdout)
        except Exception as exc:
            raise VaultError(f"Failed to parse vault init JSON: {exc}")
        # write atomic file
        self._write_keys_file_atomic(json.dumps(parsed, indent=2))
        console.print(
            f"[green]Vault initialized. Keys saved to {self.keys_file}[/green]"
        )

        return parsed

    def _unseal(self, key_data: Dict) -> None:
        console.print("\n[bold magenta]== Unsealing Vault ==[/bold magenta]")
        # check sealed status via HTTP
        ok, payload = self._http_health()
        if ok and payload is not None and payload.get("sealed") is False:
            console.print("[green]Vault already unsealed[/green]")
            return

        unseal_keys = (
            key_data.get("unseal_keys_b64")
            or key_data.get("unseal_keys_hex")
            or key_data.get("unseal_keys")
        )
        if not unseal_keys:
            raise VaultError("No unseal keys found in init data")

        # Use first threshold keys (if keys are base64 encoded, Vault CLI accepts them)
        threshold = (
            int(key_data.get("key_threshold", 3)) if "key_threshold" in key_data else 3
        )
        keys_to_use = unseal_keys[:threshold]

        console.print(
            f"Using {len(keys_to_use)} keys to unseal (threshold={threshold})"
        )

        # apply keys one by one, verifying progress after each
        for idx, key in enumerate(keys_to_use, start=1):
            console.print(f"Applying key {idx}/{len(keys_to_use)}")
            cmd = [
                "docker",
                "exec",
                self.container_name,
                "vault",
                "operator",
                "unseal",
                key,
            ]
            success, _, stderr = self.shell.run(cmd, exit_on_error=False)
            if not success:
                console.print(
                    f"[red]Unseal command failed for key {idx}: {stderr}[/red]"
                )
                raise VaultError(f"Failed to run vault unseal command: {stderr}")

            # small backoff and check sealed status
            time.sleep(0.5)
            ok2, payload2 = self._http_health()
            if ok2 and payload2 is not None and payload2.get("sealed") is False:
                console.print("[green]Vault is now unsealed[/green]")
                return

        # final check
        ok3, payload3 = self._http_health()
        if not (ok3 and payload3 is not None and payload3.get("sealed") is False):
            raise VaultError("Vault still sealed after applying unseal keys")

    def _ensure_kv_v2(self) -> None:
        console.print(
            "\n[bold magenta]== Ensuring KV v2 mounted at 'secret/' ==[/bold magenta]"
        )
        if not self.client:
            raise VaultError("HVAC client not initialized")

        # list mounts
        mounts = self.client.sys.list_mounted_secrets_engines().get("data", {})
        if "secret/" in mounts:
            # check if version is v2
            mount_info = mounts["secret/"]
            options = mount_info.get("options", {})
            version = options.get("version") or mount_info.get("options", {}).get(
                "version"
            )
            if str(version) == "2":
                console.print("[green]KV v2 already mounted at secret/[/green]")
                return
            else:
                console.print(
                    "[yellow]Mount exists at secret/ but is not v2. Reconfiguring to v2...[/yellow]"
                )

                # Attempt to disable and re-enable as v2
                self.client.sys.disable_secrets_engine(path="secret")

        # Enable KV v2 at secret/
        self.client.sys.enable_secrets_engine(
            backend_type="kv", path="secret", options={"version": "2"}
        )
        console.print("[green]KV v2 enabled at secret/[/green]")

    def get_client(self) -> hvac.Client:
        """Return an authenticated hvac client pulled from keyring if available, else raise."""
        if self.client and self.client.is_authenticated():
            return self.client
        
        try:
            token = get_vault_token_from_keyring()
        except Exception as exc:
            raise VaultError(f"Could not obtain Vault token from keyring: {exc}")
        
        client = hvac.Client(url=self.addr_host, token=token)
        if not client.is_authenticated():
            raise VaultError("Vault authentication failed with token from keyring")
        self.client = client
        return self.client
    
    def _print_summary(self, root_token: str) -> None:
        console.print("\n[bold magenta]== Vault Setup Completed ==[/bold magenta]")
        console.print(f"Root Token: [bold]{root_token}[/bold]")
        console.print(f"Keys file: [bold]{self.keys_file}[/bold]")
        console.print("For shell usage:")
        console.print(f" export VAULT_ADDR={self.addr_host}")
        console.print(f" export VAULT_TOKEN={root_token}")
