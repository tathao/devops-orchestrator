# DevOps Orchestrator CLI

A **production-ready private DevOps Orchestrator CLI** for macOS — built with **Zsh**, **Python 3.11**, and **Docker Compose**.  
This tool automates environment setup, container orchestration, Vault secrets management, and Colima virtualization.

---

## 🚀 Features

- 🧩 **Automatic Colima startup** (if available and not running)
- 🐳 **Docker Compose orchestration** with environment awareness
- 🔐 **HashiCorp Vault automation** (init, unseal, login, and agent setup)
- ⚙️ **Config-driven management** via `.env` and Python modules
- 📦 **Template-based resource creation** using Jinja2 templates
- 🧰 **Extensible CLI architecture** (easily add more services under `managers/`)
- 🪄 **Shell utilities & display helpers** for better CLI experience

---

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

---

## ⚙️ Requirements

- macOS with **Zsh shell**
- **Python 3.11+**
- **Docker Desktop** or **Colima**
- **Docker Compose v2+**
- (Optional) **HashiCorp Vault**

---

## 🔧 Setup

1. **Clone this repository**
   ```bash
   git clone https://github.com/<your-username>/<your-repo>.git
   cd <your-repo>/project
   ```

2. **Create and configure `.env` file**
   ```bash
   cp .env.example .env
   # Edit environment variables as needed
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Make CLI executable**
   ```bash
   chmod +x cli.py
   ```

---

## 🧠 Usage

### 1. Run CLI directly
```bash
python cli.py --help
```

### 2. Or create a shortcut
Add to your `.zshrc`:
```bash
alias devops="python /path/to/project/cli.py"
```
Then run:
```bash
devops up
```

---

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

---

## 🧱 Extending the CLI

To add a new command:
1. Create a new file in `managers/`, e.g. `example.py`
2. Define a class or function for the service logic
3. Register the command inside `cli.py`

---

## 🧾 License

This project is licensed under the terms of the [LICENSE](LICENSE) file.

---

## 💡 Author

**Tathao Nguyen**  
Senior Developer Engineer  
📧 Contact: (tathaonguyenl@gmail.com)
