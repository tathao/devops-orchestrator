import string
import secrets
import keyring
from config import setting
from utils.exceptions import VaultError

def generate_password(length: int = 24) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for i in range(length))

def get_vault_token_from_keyring() -> str:
    token = keyring.get_password(setting.KEYCHAIN_SERVICE_NAME, "root-token")
    if not token:
        raise VaultError("Cannot find Vault root token in KeyChain. Please run 'vault-setup' first.")
    return token

def set_vault_token_in_keyring(token: str):
    keyring.set_password(setting.KEYCHAIN_SERVICE_NAME, "root-token", token)