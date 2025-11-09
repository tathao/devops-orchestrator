import yaml
import typer
import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from config import setting
from utils.display import console
from utils.exceptions import TemplateNotFound, ServiceAlreadyExists
from managers.vault import VaultManager
from utils.security import generate_password, get_vault_token_from_keyring

class ServiceCreator:

    def __init__(self, vault_manager: VaultManager):
        self.vault_manager = vault_manager
        self.template_root = setting.TEMPLATES_DIR
        self.service_root = setting.SERVICE_DIR

    def create_service(self, template_name: str, new_service_name: str):
        console.print(f"\n[bold magenta]== Creating New Service '{new_service_name}' from Template '{template_name}' == [/bold magenta]")

        # 1. Validate paths
        template_dir, new_service_dir = self._validate_paths(template_name, new_service_name)

        # 2. Load config
        template_config = self._load_template_config(template_dir)
        console.print(f" - [italic] {template_config.get('description', 'No description')} [/italic]")

        # 3. Prompt user
        context = self._prompt_for_context(template_config)

        # 4. Handle Vault
        is_vault_integrated = "vault-agent-config.hcl.j2" in os.listdir(template_dir)
        if is_vault_integrated:
            self._handle_vault_integration(context)

        # 5. Render & Write files
        console.print("\n[bold cyan] Rendering docker-compose.yml from template... [/bold cyan]")
        self._render_and_write_templates(template_dir, new_service_dir, context, is_vault_integrated)

        # 6. Print summary
        self._print_summary(new_service_name, new_service_dir, is_vault_integrated, context)

    def _validate_paths(self, template_name: str, new_service_name: str) -> tuple[Path, Path]:
        template_dir = self.template_root / template_name
        new_service_dir = self.service_root / new_service_name

        if not template_dir.is_dir():
            raise TemplateNotFound(f"Template '{template_name}' not found in '{self.template_root}'.")
        
        if not (template_dir / "template.yml").exists() or not (template_dir / "docker-compose.j2").exists():
            raise TemplateNotFound(f"Template '{template_name}' is malformed. Missing 'template.yml' or 'docker-compose.j2'.")

        if new_service_dir.exists():
            raise ServiceAlreadyExists(f"Service '{new_service_name}' already exists in '{self.service_root}'.")
        
        return template_dir, new_service_dir
    
    def _load_template_config(self, template_dir: Path) -> dict:
        with open(template_dir / "template.yml", 'r') as f:
            return yaml.safe_load(f)
        
    def _prompt_for_context(self, template_config: dict) -> dict:
        console.print("\n[bold yellow] Please provide the following configuration values: [/bold yellow]")
        context = {}
        for var in template_config.get('variables', []):
            prompt_text = f"    {var['description']}"
            user_input = typer.prompt(prompt_text, default=var.get('default'))
            context[var['name']] = user_input
        return context
    
    def _handle_vault_integration(self, context: dict):
        console.print("\n[bold cyan] Vault integration detected. Generating and storing secrets... [/bold cyan]")
        
        secret_path = context["SECRET_PATH"]
        root_password = generate_password()
        user_password = generate_password()

        secret_data = {
            'root_password': root_password,
            'user_password': user_password
        }
        
        self.vault_manager.store_secrets(secret_path, secret_data)
        context["VAULT_TOKEN"] = get_vault_token_from_keyring()

    def _render_and_write_templates(self, template_dir: Path, new_service_dir: Path, context: dict, is_vault_integrated: bool):
        console.print(f"Creating directory: {new_service_dir}")
        new_service_dir.mkdir(parents=True)
        
        env = Environment(loader=FileSystemLoader(self.template_root))
        template_name = template_dir.name
        
        # Render docker-compose.yml
        template = env.get_template(f"{template_name}/docker-compose.j2")

        rendered_content = template.render(context)
        output_path = new_service_dir / "docker-compose.yml"
        with open(output_path, "w") as f:
            f.write(rendered_content)

        if is_vault_integrated:
            # Render vault-agent-config.hcl
            agent_template = env.get_template(f"{template_name}/vault-agent-config.hcl.j2")
            agent_config_content = agent_template.render(context)
            with open(new_service_dir / "vault-agent-config.hcl", "w") as f:
                f.write(agent_config_content)

            template_dir_for_agent = new_service_dir / "templates"
            template_dir_for_agent.mkdir()
            with open(template_dir_for_agent / "root_password.ctmpl", "w") as f:
                f.write(f'{{{{ with secret "{context["SECRET_PATH"]}" }}}}{{{{.Data.data.root_password}}}}{{{{ end }}}}')
            with open(template_dir_for_agent / "user_password.ctmpl", "w") as f:
                f.write(f'{{{{ with secret "{context["SECRET_PATH"]}" }}}}{{{{.Data.data.user_password}}}}{{{{ end }}}}')

    
    def _print_summary(self, new_service_name: str, new_service_dir: Path, is_vault_integrated: bool, context: dict):
        output_path = new_service_dir / "docker-compose.yml"
        console.print(f"[bold green] Service '{new_service_name}' created successfully! [/bold green]")
        console.print(f"    -> Configuration file written to: [cyan] {output_path} [/cyan]")
        console.print(f"    -> To start the service, run:[bold] python cli.py start {new_service_name} [/bold]")
        if is_vault_integrated:
            console.print(f"    -> To view the generated secrets, run: [bold] vault kv get {context['SECRET_PATH']} [/bold]")