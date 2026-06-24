from django.db import models
from django.contrib.auth.models import User
import os


class UserSettings(models.Model):
    """Stores per-user settings like the server home directory."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='settings')
    server_home = models.CharField(
        max_length=500,
        default=os.path.join(os.path.expanduser('~'), 'MCServers'),
        help_text='Root directory where Minecraft server folders are created.',
    )

    class Meta:
        verbose_name_plural = 'User Settings'

    def __str__(self):
        return f"Settings for {self.user.username}"


class MinecraftServer(models.Model):
    """Represents a single Minecraft server entry."""

    MOD_LOADER_CHOICES = [
        ('vanilla', 'Vanilla'),
        ('forge', 'Forge'),
        ('fabric', 'Fabric'),
        ('paper', 'Paper'),
        ('neoforge', 'NeoForge'),
        ('quilt', 'Quilt'),
        ('purpur', 'Purpur'),
        ('spigot', 'Spigot'),
        ('bukkit', 'Bukkit'),
    ]

    name = models.CharField(max_length=120)
    mc_version = models.CharField(max_length=20, verbose_name='Minecraft Version')
    mod_loader = models.CharField(max_length=20, choices=MOD_LOADER_CHOICES, default='vanilla')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='servers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.mc_version} / {self.get_mod_loader_display()})"
