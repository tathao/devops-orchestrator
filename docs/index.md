# DevOps Orchestrator CLI

A **production-ready private DevOps Orchestrator CLI** for macOS — built with **Zsh**, **Python 3.11**, and **Docker Compose**.  
This tool automates environment setup, container orchestration, Vault secrets management, and Colima virtualization.

---

## 🚀 Features

- 🧩 Automatic Colima startup (if available and not running)
- 🐳 Docker Compose orchestration with environment awareness
- 🔐 HashiCorp Vault automation (init, unseal, login, and agent setup)
- ⚙️ Config-driven management via `.env` and Python modules
- 📦 Template-based resource creation using Jinja2 templates
- 🧰 Extensible CLI architecture (easily add more services under `managers/`)
- 🪄 Shell utilities & display helpers for better CLI experience

---

## ⚙️ Requirements

- macOS with **Zsh shell**
- **Python 3.11+**
- **Docker Desktop** or **Colima**
- **Docker Compose v2+**
- (Optional) **HashiCorp Vault**
