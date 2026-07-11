from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from core_APP.models import MinecraftServer


def relay_lookup(request, server_uuid):
    server = get_object_or_404(
        MinecraftServer,
        server_uuid=server_uuid,
    )

    if not server:
        return JsonResponse({
            "error": True,
            "message": "Server not found",
        })

    if server.status != "running":
        return JsonResponse({
            "error": False,
            "server_uuid": server_uuid,
            "running": False,
        })

    return JsonResponse({
        "error": False,
        "server_uuid": server_uuid,
        "running": True,
        "port": server.port,
    })