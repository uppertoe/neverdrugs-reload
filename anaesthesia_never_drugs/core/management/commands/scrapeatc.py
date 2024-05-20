from django.core.management.base import BaseCommand

from ...tasks import import_who_atc

class Command(BaseCommand):
    help = 'Scrapes the WHO ATC'

    def handle(self, *args, **options):
        # Call your Celery task here
        result = import_who_atc.delay()