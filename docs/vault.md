## 🔐 Vault Integration

This orchestrator supports Vault operations:
- **Initialization** (`vault init`)
- **Unsealing** using stored keys
- **Login** with generated tokens
- **Template-based agent configuration**

Example:
```bash
python cli.py vault setup
```