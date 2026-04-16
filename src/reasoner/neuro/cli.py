"""
Neuro CLI
Manage the internal memory engine.
"""

import os
import sys
import json
import time
import click
import httpx
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live

from reasoner.neuro.config import load_config, NeuroConfig

console = Console()

@click.group()
def main():
    """Neuro Memory Engine CLI."""
    pass

@main.command()
def status():
    """Check health and statistics."""
    cfg = load_config()
    url = f"http://{cfg.server.host}:{cfg.server.port}/neuro/health"
    
    try:
        resp = httpx.get(url, timeout=5.0)
        data = resp.json()
        
        table = Table(title="Neuro Layer Status", show_header=False)
        table.add_row("Status", f"[green]{data['status']}[/green]" if data['status'] == "ok" else "[red]Down[/red]")
        table.add_row("Version", data['version'])
        table.add_row("Reasoning", f"{data['reasoning']['active']} (Healthy: {data['reasoning']['healthy']})")
        table.add_row("Embedding", f"{data['embedding']['active']} (Healthy: {data['embedding']['healthy']})")
        
        sess = data['sessions']
        table.add_row("Sessions", f"Hot: {sess['hot_sessions']}, Warm: {sess['warm_sessions']}, Cold: {sess['cold_sessions']}")
        
        console.print(Panel(table, title="Neuro Engine", border_style="cyan"))
    except Exception as e:
        console.print(f"[red]Error connecting to Neuro Engine:[/red] {e}")

@main.command()
@click.option("--host", default=None)
@click.option("--port", default=None, type=int)
def start(host, port):
    """Start the memory engine server."""
    import uvicorn
    cfg = load_config()
    h = host or cfg.server.host
    p = port or cfg.server.port
    console.print(f"[cyan]Starting Neuro Engine on {h}:{p}...[/cyan]")
    uvicorn.run("reasoner.neuro.server:create_neuro_router", host=h, port=p, factory=True)

if __name__ == "__main__":
    main()
