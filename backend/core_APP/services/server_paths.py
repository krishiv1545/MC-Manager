from pathlib import Path
import os


# MC_SERVER_HOME = Path(
#     os.getenv("MC_SERVER_HOME") or (Path.home() / "MCServers")
# )
MC_SERVER_HOME = Path(
    os.getenv("MC_SERVER_HOME") or Path.home() / "MCServers"
).expanduser()

# Ensure the directory exists
MC_SERVER_HOME.mkdir(parents=True, exist_ok=True)
if os.getenv("HOST_MC_SERVER_HOME"):
    HOST_MC_SERVER_HOME = Path(os.getenv("HOST_MC_SERVER_HOME")).expanduser()
    HOST_MC_SERVER_HOME.mkdir(parents=True, exist_ok=True)


def get_server_path(server_uuid):
    return MC_SERVER_HOME / str(server_uuid)


def get_host_server_path(server_uuid):
    host_root = os.getenv("HOST_MC_SERVER_HOME")

    if host_root:
        return Path(host_root) / str(server_uuid)

    return Path(os.getenv("MC_SERVER_HOME") or (Path.home() / "MCServers")) / str(server_uuid)