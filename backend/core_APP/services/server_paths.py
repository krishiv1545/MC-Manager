from pathlib import Path
import os


# MC_SERVER_HOME = Path(
#     os.getenv("MC_SERVER_HOME", str(Path.home() / "MCServers"))
# )
MC_SERVER_HOME = Path(
    os.getenv("MC_SERVER_HOME") or (Path.home() / "MCServers")
)


def get_server_path(server_uuid):
    return MC_SERVER_HOME / str(server_uuid)