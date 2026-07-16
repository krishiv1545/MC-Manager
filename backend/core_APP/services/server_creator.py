from pathlib import Path
from core_APP.models import MinecraftServer
from textwrap import dedent
import re


def get_next_port():
    latest = (
        MinecraftServer.objects
        .exclude(port__isnull=True)
        .order_by("-port")
        .first()
    )

    return (latest.port + 1) if latest else 25565


def create_server_on_disk(server, server_path):
    try:
        server_path.mkdir(parents=True, exist_ok=True)

        mem = server.memory_gb

        compose = dedent(f"""
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

        with open(server_path / "docker-compose.yml", "w") as f:
            f.write(compose)

        return True, "Server created successfully."

    except Exception as e:
        return False, f"Error creating server: {e}"


def update_compose_memory(server_path, new_memory_gb):
    """
    Patch the MEMORY environment variable in an existing docker-compose.yml
    in-place. Returns (True, message) on success, (False, message) on error.
    Preserves all other contents of the file.
    """
    compose_path = server_path / "docker-compose.yml"
    if not compose_path.exists():
        return False, "docker-compose.yml not found."

    try:
        text = compose_path.read_text(encoding="utf-8")

        # Match e.g.  MEMORY: "2G"  or  MEMORY: "2g"  (with any whitespace indent)
        updated, count = re.subn(
            r'(MEMORY:\s*")[^"]*(")',
            rf'\g<1>{new_memory_gb}G\g<2>',
            text,
        )

        if count == 0:
            return False, "MEMORY key not found in docker-compose.yml."

        compose_path.write_text(updated, encoding="utf-8")
        return True, f"Memory updated to {new_memory_gb} GB."

    except Exception as e:
        return False, f"Error updating compose file: {e}"