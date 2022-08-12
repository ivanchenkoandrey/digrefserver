from rest_framework.authentication import (TokenAuthentication,
                                           SessionAuthentication)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from auth_app.models import EventTypes, Event, Transaction, Organization


class EventListView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @classmethod
    def get(cls, request, *args, **kwargs):
        transactions_list = list(Transaction.objects.all())
        teamforce = Organization.objects.get(pk=1)
        if not Event.objects.exists():
            for transaction in transactions_list:
                if transaction.status == 'W':
                    type_to_confirm = EventTypes.objects.create(
                        name='Новая транзакция для согласования',
                        object_type='T',
                        is_personal=False,
                        has_scope=True
                    )
                    Event.objects.create(
                        event_type=type_to_confirm,
                        event_object_id=transaction.pk,
                        event_record_id=1,
                        time=transaction.updated_at,
                        scope=teamforce,
                        user=transaction.sender
                    )
                elif transaction.status == 'D':
                    type_to_declined = EventTypes.objects.create(
                        name='Исходящая транзакция отклонена',
                        object_type='T',
                        record_type='S',
                        is_personal=True,
                        has_scope=False
                    )
                    Event.objects.create(
                        event_type=type_to_declined,
                        event_object_id=transaction.pk,
                        event_record_id=1,
                        time=transaction.updated_at,
                        user=transaction.sender
                    )
                elif transaction.status == 'A':
                    type_to_accepted = EventTypes.objects.create(
                        name='Исходящая транзакция одобрена',
                        object_type='T',
                        record_type='S',
                        is_personal=True,
                        has_scope=False
                    )
                    Event.objects.create(
                        event_type=type_to_accepted,
                        event_object_id=transaction.pk,
                        event_record_id=1,
                        time=transaction.updated_at,
                        user=transaction.sender
                    )
                    Event.objects.create(
                        event_type=type_to_accepted,
                        event_object_id=transaction.pk,
                        event_record_id=1,
                        time=transaction.updated_at,
                        user=transaction.recipient
                    )
        events = [event.to_json() for event in Event.objects.all()]
        return Response(events)
