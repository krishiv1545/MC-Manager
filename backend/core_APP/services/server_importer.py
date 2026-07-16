"""
Imports an existing Minecraft server directory into MC-Manager.

Expected source layout:
    <source_dir>/
        docker-compose.yml   ← required
        data/                ← optional, copied verbatim

What it does:
    1. Reads and parses docker-compose.yml for port, VERSION, TYPE, MEMORY.
    2. Assigns a fresh UUID and a non-conflicting port.
    3. Copies the entire source directory into MC_SERVER_HOME/<uuid>/.
    4. Rewrites the docker-compose.yml with the new container name, port, and
       SERVER_PATH volume reference so MC-Manager can manage it going forward.
    5. Creates and returns a MinecraftServer DB record.
"""

import re
import shutil
import uuid as _uuid
from pathlib import Path
from textwrap import dedent

from core_APP.models import MinecraftServer
from core_APP.services.server_paths import MC_SERVER_HOME
from core_APP.services.server_creator import get_next_port


def _extract(pattern, text, default=""):
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1).strip() if m else default


def parse_compose(compose_text):
    """
    Extract server metadata from a docker-compose.yml string.
    Returns a dict: {port, mc_version, mod_loader, memory_gb}
    Falls back to safe defaults for anything that cannot be parsed.
    """
    # Host port from  ports: - "XXXX:25565"
    port_match = re.search(r'[-]\s*["\']?(\d+):25565["\']?', compose_text)
    raw_port = int(port_match.group(1)) if port_match else None

    # Environment variables
    mc_version = _extract(r'VERSION:\s*["\']?([^\s"\']+)["\']?', compose_text, default="latest")
    mod_loader  = _extract(r'TYPE:\s*["\']?([^\s"\']+)["\']?',    compose_text, default="vanilla").lower()
    memory_str  = _extract(r'MEMORY:\s*["\']?(\d+)[GgMm]?["\']?', compose_text, default="2")

    # Normalise mod_loader to our choices
    _loader_map = {
        "vanilla":  "vanilla",
        "forge":    "forge",
        "fabric":   "fabric",
        "paper":    "paper",
        "neoforge": "neoforge",
        "quilt":    "quilt",
        "purpur":   "purpur",
        "spigot":   "spigot",
        "bukkit":   "bukkit",
    }
    mod_loader = _loader_map.get(mod_loader, "vanilla")

    try:
        memory_gb = max(1, int(memory_str))
    except ValueError:
        memory_gb = 2

    return {
        "raw_port": raw_port,
        "mc_version": mc_version,
        "mod_loader": mod_loader,
        "memory_gb": memory_gb,
    }


def _build_compose(server):
    """Generate a fresh docker-compose.yml from a MinecraftServer instance."""
    mem = server.memory_gb
    return dedent(f"""
    services:
      minecraft:
        image: itzg/minecraft-server
        container_name: mc_{server.server_uuid.hex[:8]}

        ports:
          - "{server.port}:25565"

        environment:
          EULA: "TRUE"
          VERSION: "{server.mc_version}"
          TYPE: "{server.mod_loader.upper()}"
          MEMORY: "{mem}G"

        volumes:
          - "${{SERVER_PATH}}/data:/data"

        restart: unless-stopped
    """).strip()


def import_server(source_dir, server_name, owner):
    """
    Import a server from source_dir into MC-Manager.

    Parameters
    ----------
    source_dir : str | Path   Path to the directory containing docker-compose.yml
    server_name : str         Display name for the server in MC-Manager
    owner : User              Django User who will own this server

    Returns
    -------
    (True, MinecraftServer)  on success
    (False, str)             error message on failure
    """
    source = Path(source_dir)

    # Validation
    if not source.exists() or not source.is_dir():
        return False, f"Directory not found: {source}"

    compose_src = source / "docker-compose.yml"
    if not compose_src.exists():
        # Try compose.yaml as well
        compose_src = source / "compose.yaml"
        if not compose_src.exists():
            return False, "No docker-compose.yml found in the provided directory."

    # Parse the existing compose
    try:
        compose_text = compose_src.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return False, f"Could not read docker-compose.yml: {e}"

    meta = parse_compose(compose_text)

    # Assign a fresh UUID and a safe port
    new_uuid = _uuid.uuid4()
    dest_path = MC_SERVER_HOME / str(new_uuid)

    # Pick a port: try keeping the original if it's free, else get next
    desired_port = meta["raw_port"]
    port_taken = (
        desired_port is not None
        and MinecraftServer.objects.filter(port=desired_port).exists()
    )
    final_port = get_next_port() if (desired_port is None or port_taken) else desired_port

    # Copy everything from source to dest
    try:
        shutil.copytree(str(source), str(dest_path))
    except Exception as e:
        return False, f"Failed to copy server files: {e}"

    # Create the DB record
    try:
        server = MinecraftServer.objects.create(
            name=server_name,
            mc_version=meta["mc_version"],
            mod_loader=meta["mod_loader"],
            owner=owner,
            server_uuid=new_uuid,
            server_path=str(dest_path),
            port=final_port,
            status="stopped",
            memory_gb=meta["memory_gb"],
        )
    except Exception as e:
        # Clean up the copied directory if DB insert fails
        shutil.rmtree(str(dest_path), ignore_errors=True)
        return False, f"Database error: {e}"

    # Rewrite the docker-compose.yml so MC-Manager controls it
    try:
        new_compose = _build_compose(server)
        (dest_path / "docker-compose.yml").write_text(new_compose, encoding="utf-8")
        # Remove compose.yaml duplicate if present
        alt = dest_path / "compose.yaml"
        if alt.exists():
            alt.unlink()
    except Exception as e:
        return True, server

    return True, server
