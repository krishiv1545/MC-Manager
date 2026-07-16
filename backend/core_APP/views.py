from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from django.db.models import Q

from .models import MinecraftServer, ServerAccess

import uuid
import subprocess
import nbtlib
import json
from datetime import datetime
from django.urls import reverse
import os
import socket

from .services.server_creator import create_server_on_disk, update_compose_memory
from .services.server_paths import get_server_path, get_host_server_path
from .services.server_creator import get_next_port
from .services.server_importer import import_server

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
        secret_pin = request.POST.get('secretPin', '')

        if not username or not password:
            messages.error(request, 'Username and password are required.')
        elif password != confirm:
            messages.error(request, 'Passwords do not match.')
        elif secret_pin != os.getenv('SECRET_PIN'):
            messages.error(request, 'Invalid secret pin. You do not have access to create an account.')
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


# ── Helpers ──────────────────────────────────────────────────────────────────

def get_local_ipv4():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("8.8.8.8", 80))  # No packets are actually sent
        return s.getsockname()[0]
    return "localhost"  # Fallback if unable to determine


def get_accessible_server(request, server_id):
    """
    Return the MinecraftServer with the given ID if the current user is the
    owner OR has been explicitly granted access via ServerAccess.
    Raises Http404 if no such server exists at all, or if the user has no
    access to it.
    """
    server = get_object_or_404(MinecraftServer, id=server_id)
    if server.owner == request.user:
        return server
    if ServerAccess.objects.filter(server=server, user=request.user).exists():
        return server
    raise Http404("You do not have access to this server.")


# ── Dashboard views ──────────────────────────────────────────────────────────

@login_required
def dashboard_view(request):
    """Main dashboard – list all servers the current user owns or has access to."""
    owned_ids = MinecraftServer.objects.filter(owner=request.user).values_list('id', flat=True)
    granted_ids = ServerAccess.objects.filter(user=request.user).values_list('server_id', flat=True)
    all_ids = set(owned_ids) | set(granted_ids)
    servers = MinecraftServer.objects.filter(id__in=all_ids)

    for s in servers:
        s.address = f"{get_local_ipv4()}:{s.port}"
        s.is_owner = (s.owner == request.user)

    from .services.server_paths import MC_SERVER_HOME
    mc_server_home = MC_SERVER_HOME

    return render(request, 'core_APP/dashboard.html', {'servers': servers, 'mc_server_home': mc_server_home})


@login_required
def add_server_view(request):
    """Add a new Minecraft server entry."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        mc_version = request.POST.get('mc_version', '').strip()
        mod_loader = request.POST.get('mod_loader', 'vanilla')

        try:
            memory_gb = int(request.POST.get('memory_gb', 2))
            if memory_gb < 1 or memory_gb > 64:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, 'Memory must be a whole number between 1 and 64 GB.')
            return redirect('add_server')

        if not name or not mc_version:
            messages.error(request, 'Server name and version are required.')
        else:
            server_uuid = uuid.uuid4()
            server_path = get_server_path(server_uuid)

            server = MinecraftServer.objects.create(
                name=name,
                mc_version=mc_version,
                mod_loader=mod_loader,
                owner=request.user,
                server_uuid=server_uuid,
                server_path=str(server_path),
                port=get_next_port(),
                status='created',
                memory_gb=memory_gb,
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


@login_required
def load_server_view(request):
    """Import an existing Minecraft server directory into MC-Manager."""
    if request.method == 'POST':
        source_dir = request.POST.get('source_dir', '').strip()
        server_name = request.POST.get('name', '').strip()

        if not source_dir or not server_name:
            messages.error(request, 'Server name and directory path are both required.')
            return redirect('load_server')

        success, result = import_server(source_dir, server_name, request.user)

        if success:
            messages.success(request, f'Server "{server_name}" imported successfully.')
            return redirect('dashboard')
        else:
            messages.error(request, result)
            return redirect('load_server')

    return render(request, 'core_APP/load_server.html')


@require_POST
@login_required
def start_server_view(request, server_id):
    server = get_accessible_server(request, server_id)

    server_path = get_server_path(server.server_uuid)

    try:
        env = os.environ.copy()
        env["SERVER_PATH"] = str(get_host_server_path(server.server_uuid).as_posix())
        print("Starting server with SERVER_PATH:", env["SERVER_PATH"])

        subprocess.run(
            ["docker", "compose", "up", "-d"],
            cwd=server_path,
            env=env,
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
    server = get_accessible_server(request, server_id)

    server_path = get_server_path(server.server_uuid)

    try:
        env = os.environ.copy()
        env["SERVER_PATH"] = str(get_host_server_path(server.server_uuid).as_posix())

        subprocess.run(
            ["docker", "compose", "down"],
            cwd=server_path,
            env=env,
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
    server = get_accessible_server(request, server_id)

    server_properties_path = get_server_path(server.server_uuid) / "data" / "server.properties"
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
        action = request.POST.get("action")

        if action == "update_memory":
            try:
                memory_gb = int(request.POST.get("memory_gb", 2))
                if memory_gb < 1 or memory_gb > 64:
                    raise ValueError
                server.memory_gb = memory_gb
                server.save()
                
                success, msg = update_compose_memory(get_server_path(server.server_uuid), memory_gb)
                if success:
                    messages.success(request, msg)
                else:
                    messages.error(request, msg)
            except (ValueError, TypeError):
                messages.error(request, "Memory must be a whole number between 1 and 64 GB.")
            return redirect("edit_server", server.id)

        elif action == "update_server_name":
            server.name = request.POST.get("server_name", server.name)
            server.save()
            messages.success(request, "Server name updated.")
            return redirect("edit_server", server.id)
            
        elif action == "update_properties" or not action:
            # Fallback for empty action or update_properties
            lines = []
            if server_properties_path.exists():
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
        'is_owner': server.owner == request.user,
    })


@login_required
def manage_access_view(request, server_id):
    """
    Owner-only view to grant or revoke access to a server.
    Shared users receive a 403 Forbidden response.
    """
    server = get_object_or_404(MinecraftServer, id=server_id)

    if server.owner != request.user:
        messages.error(request, "You are not the owner of this server.")
        return redirect("dashboard")

    if request.method == "POST":
        action = request.POST.get("action")
        user_id = request.POST.get("user_id")

        if not user_id:
            messages.error(request, "No user selected.")
            return redirect("manage_access", server_id=server_id)

        target_user = get_object_or_404(User, id=user_id)

        if target_user == request.user:
            messages.error(request, "You cannot modify access for yourself.")
            return redirect("manage_access", server_id=server_id)

        if action == "grant":
            _, created = ServerAccess.objects.get_or_create(
                server=server,
                user=target_user,
                defaults={'granted_by': request.user},
            )
            if created:
                messages.success(request, f"Access granted to {target_user.username}.")
            else:
                messages.info(request, f"{target_user.username} already has access.")

        elif action == "revoke":
            deleted, _ = ServerAccess.objects.filter(server=server, user=target_user).delete()
            if deleted:
                messages.success(request, f"Access revoked for {target_user.username}.")
            else:
                messages.error(request, f"{target_user.username} did not have access.")

        return redirect("manage_access", server_id=server_id)

    # Build list of currently-granted users
    access_grants = ServerAccess.objects.filter(server=server).select_related('user', 'granted_by')
    granted_user_ids = set(ag.user_id for ag in access_grants)

    # All users except the owner and those already granted
    available_users = User.objects.exclude(id=request.user.id).exclude(id__in=granted_user_ids)

    return render(request, 'core_APP/manage_access.html', {
        'server': server,
        'access_grants': access_grants,
        'available_users': available_users,
    })


@login_required
def playerdata_view(request, server_id):
    """View player data for a specific server."""

    server = get_accessible_server(request, server_id)

    if request.method == "POST":
        action = request.POST.get("action")
        target_uuid = request.POST.get("player_uuid")

        if not target_uuid:
            messages.error(request, "No player selected.")
            return redirect(request.path)

        player_file = get_server_path(server.server_uuid) / "data" / "world" / "playerdata" / f"{target_uuid}.dat"
        server_root = get_server_path(server.server_uuid) / "data"

        # First, resolve the username for RCON commands
        username = target_uuid
        usercache_path = server_root / "usercache.json"
        if usercache_path.exists():
            try:
                with open(usercache_path, "r") as f:
                    cache = json.load(f)
                    for entry in cache:
                        if entry.get("uuid") == target_uuid:
                            username = entry.get("name", target_uuid)
                            break
            except:
                pass

        is_running = server.status == "running"
        container_name = f"mc_{server.server_uuid.hex[:8]}"

        def run_rcon(cmd_str):
            if not is_running: return False
            try:
                subprocess.run(
                    ["docker", "exec", container_name, "rcon-cli"] + cmd_str.split(),
                    check=True, capture_output=True
                )
                return True
            except:
                return False

        try:
            if action in ["kill", "heal", "starve", "feed", "teleport"]:
                if is_running:
                    if action == "kill": run_rcon(f"kill {username}")
                    elif action == "heal": run_rcon(f"effect give {username} minecraft:instant_health 1 100")
                    elif action == "starve": run_rcon(f"effect give {username} minecraft:hunger 10 100")
                    elif action == "feed": run_rcon(f"effect give {username} minecraft:saturation 1 100")
                    elif action == "teleport":
                        dim = request.POST.get("dimension", "minecraft:overworld")
                        x = request.POST.get("x", "0")
                        y = request.POST.get("y", "0")
                        z = request.POST.get("z", "0")
                        run_rcon(f"execute in {dim} run tp {username} {x} {y} {z}")
                    messages.success(request, f"Executed {action} on {username} (live).")
                else:
                    if not player_file.exists():
                        messages.error(request, "Player data not found.")
                        return redirect(f"{request.path}?player={target_uuid}")

                    nbt_file = nbtlib.load(player_file)
                    
                    if action == "kill":
                        nbt_file["Health"] = nbtlib.tag.Float(0.0)
                        nbt_file.save()
                        messages.success(request, f"Killed player.")
                    elif action == "heal":
                        nbt_file["Health"] = nbtlib.tag.Float(20.0)
                        nbt_file.save()
                        messages.success(request, f"Healed player.")
                    elif action == "starve":
                        nbt_file["foodLevel"] = nbtlib.tag.Int(0)
                        nbt_file.save()
                        messages.success(request, f"Starved player.")
                    elif action == "feed":
                        nbt_file["foodLevel"] = nbtlib.tag.Int(20)
                        nbt_file.save()
                        messages.success(request, f"Fed player.")
                    elif action == "teleport":
                        dim = request.POST.get("dimension", "minecraft:overworld")
                        try:
                            x = float(request.POST.get("x", 0))
                            y = float(request.POST.get("y", 0))
                            z = float(request.POST.get("z", 0))
                        except ValueError:
                            x, y, z = 0.0, 0.0, 0.0
                        
                        nbt_file["Dimension"] = nbtlib.tag.String(dim)
                        nbt_file["Pos"] = nbtlib.tag.List[nbtlib.tag.Double]([nbtlib.tag.Double(x), nbtlib.tag.Double(y), nbtlib.tag.Double(z)])
                        nbt_file.save()
                        messages.success(request, f"Teleported player to {x}, {y}, {z} in {dim}.")

            elif action in ["op", "deop", "whitelist_add", "whitelist_remove", "ban", "unban"]:
                if is_running:
                    if action == "op": run_rcon(f"op {username}")
                    elif action == "deop": run_rcon(f"deop {username}")
                    elif action == "whitelist_add": run_rcon(f"whitelist add {username}")
                    elif action == "whitelist_remove": run_rcon(f"whitelist remove {username}")
                    elif action == "ban": run_rcon(f"ban {username}")
                    elif action == "unban": run_rcon(f"pardon {username}")
                    messages.success(request, f"Executed {action} on {username} (live).")
                
                # We also write to the JSON files as a fallback / to keep them in sync

                if action in ["op", "deop"]:
                    ops_path = server_root / "ops.json"
                    ops = []
                    if ops_path.exists():
                        try:
                            with open(ops_path, "r") as f:
                                ops = json.load(f)
                        except:
                            pass
                    
                    ops = [op for op in ops if op.get("uuid") != target_uuid]
                    if action == "op":
                        ops.append({
                            "uuid": target_uuid,
                            "name": username,
                            "level": 4,
                            "bypassesPlayerLimit": False
                        })
                        messages.success(request, f"Opped player {username}.")
                    else:
                        messages.success(request, f"Deopped player {username}.")
                        
                    with open(ops_path, "w") as f:
                        json.dump(ops, f, indent=2)

                elif action in ["whitelist_add", "whitelist_remove"]:
                    wl_path = server_root / "whitelist.json"
                    wl = []
                    if wl_path.exists():
                        try:
                            with open(wl_path, "r") as f:
                                wl = json.load(f)
                        except:
                            pass
                    
                    wl = [w for w in wl if w.get("uuid") != target_uuid]
                    if action == "whitelist_add":
                        wl.append({
                            "uuid": target_uuid,
                            "name": username
                        })
                        messages.success(request, f"Whitelisted player {username}.")
                    else:
                        messages.success(request, f"Removed player {username} from whitelist.")
                        
                    with open(wl_path, "w") as f:
                        json.dump(wl, f, indent=2)

                elif action in ["ban", "unban"]:
                    bans_path = server_root / "banned-players.json"
                    bans = []
                    if bans_path.exists():
                        try:
                            with open(bans_path, "r") as f:
                                bans = json.load(f)
                        except:
                            pass
                    
                    bans = [b for b in bans if b.get("uuid") != target_uuid]
                    if action == "ban":
                        bans.append({
                            "uuid": target_uuid,
                            "name": username,
                            "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S Z"),
                            "source": "Server",
                            "expires": "forever",
                            "reason": "Banned by an operator."
                        })
                        messages.success(request, f"Banned player {username}.")
                    else:
                        messages.success(request, f"Unbanned player {username}.")
                        
                    with open(bans_path, "w") as f:
                        json.dump(bans, f, indent=2)
                        
            return redirect(f"{request.path}?player={target_uuid}")
        except Exception as e:
            messages.error(request, f"Error: {e}")
            return redirect(f"{request.path}?player={target_uuid}")

    playerdata_path = get_server_path(server.server_uuid) / "data" / "world" / "playerdata"

    server_root = get_server_path(server.server_uuid) / "data"
    ops = []
    whitelist = []
    bans = []
    try:
        if (server_root / "ops.json").exists():
            with open(server_root / "ops.json", "r") as f:
                ops = json.load(f)
    except: pass
    try:
        if (server_root / "whitelist.json").exists():
            with open(server_root / "whitelist.json", "r") as f:
                whitelist = json.load(f)
    except: pass
    try:
        if (server_root / "banned-players.json").exists():
            with open(server_root / "banned-players.json", "r") as f:
                bans = json.load(f)
    except: pass

    op_uuids = {op.get("uuid") for op in ops if op.get("uuid")}
    whitelist_uuids = {w.get("uuid") for w in whitelist if w.get("uuid")}
    ban_uuids = {b.get("uuid") for b in bans if b.get("uuid")}

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
                "is_op": file.stem in op_uuids,
                "is_whitelisted": file.stem in whitelist_uuids,
                "is_banned": file.stem in ban_uuids,
                "last_death_location": {
                    "dimension": str(nbt.get("LastDeathLocation", {}).get("dimension", "")),
                    "pos": nbt.get("LastDeathLocation", {}).get("pos", [])
                } if nbt.get("LastDeathLocation") else None,
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
        "is_owner": server.owner == request.user,
    })