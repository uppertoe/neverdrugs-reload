from django.core.management.base import BaseCommand

from ...tasks import dispatch_orphanet_imports

class Command(BaseCommand):
    help = 'Scrapes the Orphanet database'

    def handle(self, *args, **options):
        # Call your Celery task here
        result = dispatch_orphanet_imports.delay()