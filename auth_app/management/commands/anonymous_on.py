from django.core.management.base import BaseCommand
from auth_app.models import Setting


class Command(BaseCommand):

    help = 'Set or update anonymous settings in the database'

    def handle(self, *args, **options):
        anonymous_settings = Setting.objects.filter(name='anonymous_mode').first()
        if anonymous_settings is not None:
            anonymous_settings.value = 'on'
            anonymous_settings.save()
            self.stdout.write('Anonymous mode setting was updated to ON.')
        else:
            Setting.objects.create(
                name='anonymous_mode',
                value='on'
            )
            self.stdout.write('Anonymous mode (on) setting was created just now.')
