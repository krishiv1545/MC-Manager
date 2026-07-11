from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from core_APP.models import MinecraftServer


def relay_lookup(request, server_uuid):
    server = get_object_or_404(
        MinecraftServer,
        server_uuid=server_uuid,
    )

    if server.status != "running":
        return JsonResponse({
            "server_uuid": server_uuid,
            "running": False,
        })

    return JsonResponse({
        "server_uuid": server_uuid,
        "running": True,
        "port": server.port,
    })