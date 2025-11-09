# 🐬 MySQL + phpMyAdmin + Vault Agent Template

## 📘 Overview

This template deploys a **standalone MySQL 8.0 server** with **phpMyAdmin** UI,
secured by **HashiCorp Vault Agent integration** for secret injection.

The Vault Agent automatically retrieves and refreshes database credentials from Vault,
mounting them as files inside the MySQL container at runtime — eliminating the need to hardcode secrets.

This setup is designed to work seamlessly with Docker Compose, Colima (macOS), and a running Vault service.

---

## 🧩 Components

| Service | Description |
|----------|--------------|
| **mysql** | MySQL 8.0 database container, configured with secrets read from Vault |
| **phpmyadmin** | Web-based management UI for MySQL |
| **vault-agent** | HashiCorp Vault Agent that authenticates and renders secrets to mounted files |

---

## 📁 Template Files

| File | Purpose |
|------|----------|
| `docker-compose.j2` | Jinja2-based Docker Compose template for MySQL, phpMyAdmin, and Vault Agent |
| `template.yml` | Variable definition and description for the template generator |
| `vault-agent-config.hcl.j2` | Vault Agent configuration for secret rendering and token authentication |
| `_vault_agent.j2` | Shared Jinja macro used to inject the Vault Agent service configuration |

---

## ⚙️ Configuration Variables

Defined in `template.yml`.

| Variable | Description | Default |
|-----------|--------------|----------|
| `CONTAINER_NAME` | Base name for all containers (e.g. `mysql-db`) | `mysql-db` |
| `MYSQL_PORT` | Public port for MySQL access | `3306` |
| `PHPMYADMIN_PORT` | Port for phpMyAdmin web UI | `8080` |
| `MYSQL_DATABASE` | Initial database name | `my_db` |
| `MYSQL_USER` | MySQL username | `my_user` |
| `SECRET_PATH` | Vault path containing secrets | `secret/data/mysql-db` |

> 💡 The Vault secret at `${SECRET_PATH}` should contain the following fields:
> ```json
> {
>   "data": {
>     "root_password": "<root_password_value>",
>     "user_password": "<user_password_value>"
>   }
> }
> ```

---

## 🔐 Vault Agent Integration

The Vault Agent is configured to:
1. Authenticate to Vault using a **static token** (mounted at `/var/run/secrets/vault_token`).
2. Render secrets from Vault to local files:
   - `/vault/secrets/root_password`
   - `/vault/secrets/user_password`
3. These files are then consumed by the MySQL container through `_FILE` environment variables:
   ```yaml
   MYSQL_ROOT_PASSWORD_FILE: /vault/secrets/root_password
   MYSQL_PASSWORD_FILE: /vault/secrets/user_password

---

## 🧠 Secret Template Rendering

From vault-agent-config.hcl.j2:
```hcl
template {
  source      = "/vault/secrets/templates/root_password.ctmpl"
  destination = "/vault/secrets/root_password"
}

template {
  source      = "/vault/secrets/templates/user_password.ctmpl"
  destination = "/vault/secrets/user_password"
}
```

Each .ctmpl file uses Vault template syntax to pull data, for example:
```hcl
{{ with secret "secret/data/mysql-db" }}
{{ .Data.data.root_password }}
{{ end }}
```