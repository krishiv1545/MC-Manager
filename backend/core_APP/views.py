from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import UserSettings, MinecraftServer

import uuid

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
            from .services.server_creator import create_server_on_disk
            from .services.server_paths import get_server_path
            from .services.server_creator import get_next_port

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
