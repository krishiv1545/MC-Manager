from django.db import models
from django.contrib.auth.models import User
import os
import uuid


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

    STATUS_CHOICES = [
        ("created", "Created"),
        ("running", "Running"),
        ("stopped", "Stopped"),
        ("starting", "Starting"),
        ("stopping", "Stopping"),
        ("error", "Error"),
    ]
    server_uuid = models.UUIDField(
        unique=True,
        editable=False,
        default=uuid.uuid4,
    )
    server_path = models.CharField(
        max_length=1000,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="created",
    )
    port = models.PositiveIntegerField(
        unique=True,
        null=True,
        blank=True,
    )
    memory_gb = models.PositiveIntegerField(
        default=2,
        verbose_name='Memory (GB)',
        help_text='RAM limit for the Minecraft server container in gigabytes.',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.mc_version} / {self.get_mod_loader_display()})"


class ServerAccess(models.Model):
    """Grants a user the ability to view and manage a server they do not own."""

    server = models.ForeignKey(
        MinecraftServer,
        on_delete=models.CASCADE,
        related_name='access_grants',
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='server_access',
    )
    granted_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='access_granted_by',
    )
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('server', 'user')
        ordering = ['granted_at']

    def __str__(self):
        return f"{self.user.username} → {self.server.name} (granted by {self.granted_by.username})"
