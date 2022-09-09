import os

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        base_directory = os.getcwd()
        for item in os.listdir(base_directory):
            if item.endswith('.xlsx'):
                os.remove(item)
