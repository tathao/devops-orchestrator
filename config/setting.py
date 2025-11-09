import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent.resolve() 

SERVICE_DIR = BASE_DIR / "services"
TEMPLATES_DIR = BASE_DIR / "templates"

DOCKER_EXTERNAL_NETWORK = os.getenv("DOCKER_EXTERNAL_NETWORK")

KEYCHAIN_SERVICE_NAME = "private-orchestrator-vault"
VAULT_ADDR = "http://127.0.0.1:8200"
VAULT_SERVICE_DIR = SERVICE_DIR / "vault"
VAULT_CONTAINER_NAME = "vault"
VAULT_KEYS_FILE = VAULT_SERVICE_DIR / ".vault_keys"