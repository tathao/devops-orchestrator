from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod

import docker
from rich.table import Table
from rich.text import Text
from utils.display import console
# -------------------
# Domain Model
# -------------------
@dataclass(frozen=True)
class ContainerInfo:
    id: str
    name: str
    image: str
    status: str
    created: str
    ports: str

# -------------------
# Abstract Interfaces
# -------------------
class ContainerRepository(ABC):

    @abstractmethod
    def list_containers(self, include_all: bool = False) -> List[ContainerInfo]:
        pass

class OutputRenderer(ABC):

    @abstractmethod
    def render(self, containers: List[ContainerInfo]) -> None:
        pass

# -------------------
# Helpers
# -------------------
class DockerFormatters:

    @staticmethod
    def format_ports(ports: Optional[Dict[str, Any]]) -> str:
        if not ports:
            return ""
        parts = []
        for container_port, bindings in ports.items():
            if not bindings:
                parts.append(f"{container_port}->(unbound)")
            else:
                binds = ", ".join(f"{b['HostIp']}:{b['HostPort']}" for b in bindings)
                parts.append(f"{container_port}->{binds}")
        return "; ".join(parts)
    
    @staticmethod
    def format_created(timestamp: str) -> str:
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return timestamp
        
# -------------------
# Implementation
# -------------------
class DockerSDKRepository(ContainerRepository):
    def __init__(self) -> None:
        self.client = docker.from_env()

    def list_containers(self, include_all: bool = False) -> List[ContainerInfo]:
        containers = self.client.containers.list(all=include_all)
        result: List[ContainerInfo] = []
        for c in containers:
            image_name = c.image.tags[0] if c.image.tags else str(c.image)
            created = DockerFormatters.format_created(c.attrs.get("Created", ""))
            ports = DockerFormatters.format_ports(
                c.attrs.get("NetworkSettings", {}).get("Ports")
            )
            info = ContainerInfo(
                id=c.short_id,
                name=c.name,
                image=image_name,
                status=c.status,
                created=created,
                ports=ports,
            )
            result.append(info)
        return result
    
# -------------------
# Renderers
# -------------------
class TableRenderer(OutputRenderer):
    STATUS_COLORS = {
        "running": "green",
        "exited": "red",
        "paused": "yellow",
        "restarting": "magenta",
    }

    def render(self, containers: List[ContainerInfo]) -> None:

        if not containers:
            console.print("[bold yellow]No containers found.[/bold yellow]")
            return

        table = self._create_table()

        self._populate_table(table, containers)
        
        console.print("\n[bold cyan]📦 Docker Containers:[/bold cyan]\n")
        console.print(table)

    def _create_table(self) -> Table:
        table = Table(show_header=True, header_style="bold magenta", 
                      border_style="dim", highlight=True, row_styles=["none", "dim"])
        table.add_column("CONTAINER ID", style="cyan", no_wrap=True)
        table.add_column("NAME", style="bold green")
        table.add_column("IMAGE", style="white")
        table.add_column("STATUS", style="bold")
        table.add_column("CREATED", style="dim")
        table.add_column("PORTS", style="yellow")
        return table
    
    def _populate_table(self, table: Table, containers: List[ContainerInfo]) -> None:
        for c in containers:
            status_color = self._get_status_color(c.status)
            table.add_row(
                c.id[:12],
                c.name,
                c.image,
                Text(c.status, style=status_color),
                c.created,
                c.ports or "N/A"
            )

    def _get_status_color(self, status: str) -> str:
        for key, color in self.STATUS_COLORS.items():
            if key in status.lower():
                return color
        return "white"

# -------------------
# Service
# -------------------
class ContainerService:
    def __init__(self, repository: ContainerRepository, renderer: OutputRenderer) -> None:
        self.repository = repository
        self.renderer = renderer

    def list_and_render_containers(self, include_all: bool = False) -> None:
        containers = self.repository.list_containers(include_all=include_all)
        self.renderer.render(containers)