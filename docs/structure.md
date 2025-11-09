## 🏗️ Project Structure

```
project/
├── cli.py                   # Main CLI entry point
├── .env                     # Environment configuration
├── config/
│   ├── setting.py           # Global config and environment loader
├── managers/
│   ├── colima.py            # Colima lifecycle management
│   ├── docker.py            # Docker orchestration logic
│   ├── vault.py             # HashiCorp Vault automation
│   ├── creator.py           # Template-based resource creator
│   └── service.py           # Common service manager
├── utils/
│   ├── shell.py             # Shell command runner
│   ├── security.py          # Security utilities (e.g., secret handling)
│   ├── display.py           # Display and logging helpers
│   ├── exceptions.py        # Centralized exception definitions
├── templates/
│   ├── _vault_agent.j2      # Vault agent template
│   ├── mysql_vault/
│   │   ├── template.yml
│   │   ├── vault-agent-config.hcl.j2
│   │   └── docker-compose.j2
└── LICENSE
```