from django.core.management.base import BaseCommand
from django.db import transaction

from auth_app.models import Event, EventTypes, Transaction, Challenge, ChallengeReport


class Command(BaseCommand):
    def handle(self, *args, **options):
        transaction_event_type = EventTypes.objects.get_or_create(name='Новая публичная транзакция')[0]
        challenge_event_type = EventTypes.objects.get_or_create(name='Создан челлендж',
                                                                is_personal=False, has_scope=True)[0]
        challenge_winner_event_type = EventTypes.objects.get_or_create(name='Новый победитель челленджа',
                                                                       is_personal=False, has_scope=True)[0]
        transactions = Transaction.objects.filter(is_public=True, status='R').only('pk', 'updated_at')
        challenges = Challenge.objects.only('pk')
        challenge_winners_reports = ChallengeReport.objects.filter(state='W').only('pk', 'updated_at')
        with transaction.atomic():
            for t in transactions:
                Event.objects.create(
                    event_type=transaction_event_type,
                    event_object_id=t.pk,
                    time=t.updated_at,
                    object_selector='T'
                )
            for c in challenges:
                Event.objects.create(
                    event_type=challenge_event_type,
                    event_object_id=c.pk,
                    time=c.updated_at,
                    object_selector='Q'
                )
            for cr in challenge_winners_reports:
                Event.objects.create(
                    event_type=challenge_winner_event_type,
                    event_object_id=cr.pk,
                    time=cr.updated_at,
                    object_selector='R'
                )
