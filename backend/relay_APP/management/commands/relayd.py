from django.core.management.base import BaseCommand

from relay_APP.relay_daemon import run


class Command(BaseCommand):
    help = "Starts the relay daemon"

    def handle(self, *args, **kwargs):
        run()