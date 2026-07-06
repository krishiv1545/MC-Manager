from pathlib import Path


def get_server_path(user_settings, server_uuid):
    return (
        Path(user_settings.server_home)
        / str(server_uuid)
    )