import requests


def lookup(server_uuid):
    r = requests.get(
        f"http://127.0.0.1:8000/relay/{server_uuid}/",
        timeout=3,
    )

    r.raise_for_status()

    return r.json()