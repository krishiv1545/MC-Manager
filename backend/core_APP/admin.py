from django.contrib import admin
from .models import MinecraftServer, ServerAccess


@admin.register(MinecraftServer)
class MinecraftServerAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'mc_version', 'mod_loader', 'memory_gb', 'status', 'port', 'created_at')
    list_filter = ('status', 'mod_loader')
    search_fields = ('name', 'owner__username')


@admin.register(ServerAccess)
class ServerAccessAdmin(admin.ModelAdmin):
    list_display = ('server', 'user', 'granted_by', 'granted_at')
    list_filter = ('server',)
    search_fields = ('user__username', 'server__name')
