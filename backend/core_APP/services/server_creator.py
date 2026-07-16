from pathlib import Path
from core_APP.models import MinecraftServer
from textwrap import dedent


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