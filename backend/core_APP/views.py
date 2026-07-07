from pprint import pprint

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404

from .models import UserSettings, MinecraftServer

import uuid
import subprocess
import nbtlib

from .services.server_creator import create_server_on_disk
from .services.server_paths import get_server_path
from .services.server_creator import get_next_port

# ── Auth views ───────────────────────────────────────────────────────────────

def login_view(request):
    """GET: show login form.  POST: authenticate and redirect to dashboard."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        remember = request.POST.get('remember')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if not remember:
                request.session.set_expiry(0)  # session expires on browser close
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'core_APP/login.html')


def signup_view(request):
    """GET: show signup form.  POST: create user, redirect to login."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        confirm = request.POST.get('confirm', '')

        if not username or not password:
            messages.error(request, 'Username and password are required.')
        elif password != confirm:
            messages.error(request, 'Passwords do not match.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken.')
        else:
            User.objects.create_user(username=username, password=password)
            messages.success(request, 'Account created! Please log in.')
            return redirect('login')

    return render(request, 'core_APP/signup.html')


def logout_view(request):
    """Log out and redirect to login page."""
    logout(request)
    return redirect('login')


# ── Dashboard views ──────────────────────────────────────────────────────────

@login_required
def dashboard_view(request):
    """Main dashboard – list all servers owned by the current user."""
    servers = MinecraftServer.objects.filter(owner=request.user)
    return render(request, 'core_APP/dashboard.html', {'servers': servers})


@login_required
def settings_view(request):
    """View / update the server home directory."""
    settings_obj, _ = UserSettings.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        new_home = request.POST.get('server_home', '').strip()
        if new_home:
            settings_obj.server_home = new_home
            settings_obj.save()
            messages.success(request, 'Server home directory updated.')
        else:
            messages.error(request, 'Path cannot be empty.')

    return render(request, 'core_APP/settings.html', {'settings': settings_obj})


@login_required
def add_server_view(request):
    """Add a new Minecraft server entry."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        mc_version = request.POST.get('mc_version', '').strip()
        mod_loader = request.POST.get('mod_loader', 'vanilla')

        if not name or not mc_version:
            messages.error(request, 'Server name and version are required.')
        else:
            server_uuid = uuid.uuid4()
            server_path = get_server_path(request.user.settings, server_uuid)

            server = MinecraftServer.objects.create(
                name=name,
                mc_version=mc_version,
                mod_loader=mod_loader,
                owner=request.user,
                server_uuid=server_uuid,
                server_path=str(server_path),
                port=get_next_port(),
                status='created',
            )

            success, message = create_server_on_disk(server, server_path)
            if not success:
                server.delete()  # Rollback if creation failed
                messages.error(request, message)
            else:
                server.save()
                messages.success(request, f'Server "{name}" created.')
            
            return redirect('dashboard')

    loader_choices = MinecraftServer.MOD_LOADER_CHOICES
    return render(request, 'core_APP/add_server.html', {'loader_choices': loader_choices})


@require_POST
@login_required
def start_server_view(request, server_id):
    server = get_object_or_404(
        MinecraftServer,
        id=server_id,
        owner=request.user,
    )

    server_path = get_server_path(request.user.settings, server.server_uuid)

    try:
        subprocess.run(
            ["docker", "compose", "up", "-d"],
            cwd=server_path,
            capture_output=True,
            text=True,
            check=True,
        )

        server.status = "running"
        server.save()

        messages.success(request, f"{server.name} started.")

    except subprocess.CalledProcessError as e:
        server.status = "error"
        server.save()

        messages.error(request, e.stderr)

    return redirect("dashboard")


@require_POST
@login_required
def stop_server_view(request, server_id):
    server = get_object_or_404(
        MinecraftServer,
        id=server_id,
        owner=request.user,
    )

    server_path = get_server_path(request.user.settings, server.server_uuid)

    try:
        subprocess.run(
            ["docker", "compose", "down"],
            cwd=server_path,
            capture_output=True,
            text=True,
            check=True,
        )

        server.status = "stopped"
        server.save()

        messages.success(request, f"{server.name} stopped.")

    except subprocess.CalledProcessError as e:
        server.status = "error"
        server.save()

        messages.error(request, e.stderr)

    return redirect("dashboard")


@login_required
def edit_server_view(request, server_id):
    """View and edit a specific server's settings."""
    server = get_object_or_404(
        MinecraftServer,
        id=server_id,
        owner=request.user,
    )

    server_properties_path = get_server_path(request.user.settings, server.server_uuid) / "data" / "server.properties"
    print(server_properties_path)

    properties = {}

    # Read Server Properties
    if server_properties_path.exists():
        with open(server_properties_path, 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    properties[key] = value

    if request.method == "POST":
        lines = []
        with open(server_properties_path, "r") as f:
            for line in f:
                if "=" in line and not line.lstrip().startswith("#"):
                    key, _ = line.rstrip("\n").split("=", 1)

                    if key in request.POST:
                        value = request.POST[key]
                        line = f"{key}={value}\n"

                lines.append(line)

        with open(server_properties_path, "w") as f:
            f.writelines(lines)

        messages.success(request, "Server properties updated.")
        return redirect("edit_server", server.id)

    return render(request, 'core_APP/edit_server.html', {
        'server': server,
        'properties': properties,
    })


@login_required
def playerdata_view(request, server_id):
    """View player data for a specific server."""

    server = get_object_or_404(
        MinecraftServer,
        id=server_id,
        owner=request.user,
    )

    playerdata_path = get_server_path(request.user.settings, server.server_uuid) / "data" / "world" / "playerdata"

    players = []

    if playerdata_path.exists():
        for file in playerdata_path.glob("*.dat"):

            nbt = nbtlib.load(file).unpack()

            inventory = [None] * 36

            for item in nbt.get("Inventory", []):
                slot = item["Slot"]

                # Ignore armor/offhand for now
                if 0 <= slot < 36:
                    inventory[slot] = {
                        "slot": slot,
                        "id": item["id"],
                        "name": item["id"].replace("minecraft:", "").replace("_", " ").title(),
                        "texture": item["id"].replace("minecraft:", "") + ".png",
                        "count": item["count"],
                    }

            ender = [None] * 27

            for i, item in enumerate(nbt.get("EnderItems", [])):
                if i < 27:
                    ender[i] = {
                        "id": item["id"],
                        "name": item["id"].replace("minecraft:", "").replace("_", " ").title(),
                        "texture": item["id"].replace("minecraft:", "") + ".png",
                        "count": item["count"],
                    }

            abilities = nbt.get("abilities", {})

            attributes = [
                {
                    "id": a["id"].replace("minecraft:", ""),
                    "base": a["base"],
                }
                for a in nbt.get("attributes", [])
            ]

            players.append({
                "uuid": file.stem,
                "name": file.stem,          # Replace later with username lookup
                "health": nbt.get("Health", 20),
                "food": nbt.get("foodLevel", 20),
                "xp_level": nbt.get("XpLevel", 0),
                "xp_total": nbt.get("XpTotal", 0),
                "xp_progress": nbt.get("XpP", 0),

                "gamemode": {
                    0: "Survival",
                    1: "Creative",
                    2: "Adventure",
                    3: "Spectator",
                }.get(nbt.get("playerGameType", 0), "Unknown"),

                "dimension": nbt.get("Dimension"),
                "pos": nbt.get("Pos", [0, 0, 0]),
                "rotation": nbt.get("Rotation", [0, 0]),

                "spawn_dimension": nbt.get("SpawnDimension"),
                "spawn_x": nbt.get("SpawnX"),
                "spawn_y": nbt.get("SpawnY"),
                "spawn_z": nbt.get("SpawnZ"),
                "spawn_angle": nbt.get("SpawnAngle"),

                "on_ground": bool(nbt.get("OnGround", 0)),
                "air": nbt.get("Air"),
                "fire": nbt.get("Fire"),
                "fall_distance": nbt.get("FallDistance"),
                "portal_cooldown": nbt.get("PortalCooldown"),

                "flying": bool(abilities.get("flying", 0)),
                "invulnerable": bool(abilities.get("invulnerable", 0)),
                "mayfly": bool(abilities.get("mayfly", 0)),

                "food_saturation": nbt.get("foodSaturationLevel"),
                "food_exhaustion": nbt.get("foodExhaustionLevel"),

                "score": nbt.get("Score"),
                "seen_credits": bool(nbt.get("seenCredits", 0)),
                "motion": nbt.get("Motion"),

                "attributes": attributes,

                "selected_slot": nbt.get("SelectedItemSlot", 0),

                "inventory": inventory,
                "ender": ender,

                "data_version": nbt.get("DataVersion"),
            })

    selected_uuid = request.GET.get("player")

    selected_player = None

    if players:
        if selected_uuid:
            selected_player = next(
                (p for p in players if p["uuid"] == selected_uuid),
                players[0]
            )
        else:
            selected_player = players[0]

    return render(request, "core_APP/playerdata.html", {
        "server": server,
        "players": players,
        "selected_player": selected_player,
        "inventory_slots": (selected_player["inventory"][9:] + selected_player["inventory"][:9]) if selected_player else [],
        "ender_slots": selected_player["ender"] if selected_player else [],
    })