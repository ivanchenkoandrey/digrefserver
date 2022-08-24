from rest_framework.authentication import (TokenAuthentication,
                                           SessionAuthentication)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from auth_app.models import EventTypes, Transaction


def get_event_type(user, transaction, event_types):
    if transaction.is_public is True and transaction.recipient != user:
        return event_types.get(name='Новая публичная транзакция')
    return event_types.get(name='Входящая транзакция')


class EventListView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @classmethod
    def get(cls, request, *args, **kwargs):
        if not EventTypes.objects.exists():
            EventTypes.objects.create(
                name='Входящая транзакция',
                object_type='T',
                is_personal=True,
                has_scope=True
            )
            EventTypes.objects.create(
                name='Новая публичная транзакция',
                object_type='T',
                is_personal=False,
                has_scope=True
            )
        public_transactions = (Transaction.objects.select_related('sender__profile', 'recipient__profile')
                               .filter(is_public=True, status='A')
                               .exclude(recipient=request.user))
        transactions_receiver_only = (Transaction.objects.select_related('sender__profile', 'recipient__profile')
                                      .filter(recipient=request.user, status='A'))
        extended_queryset = (public_transactions | transactions_receiver_only).distinct().order_by('-updated_at')[:25]
        event_types = EventTypes.objects.all()
        feed_data = []
        for transaction in extended_queryset:
            event_type = get_event_type(request.user, transaction, event_types).to_json()
            sender = 'anonymous' if transaction.is_anonymous else transaction.sender.profile.tg_name
            del event_type['record_type']
            event_data = {
                "id": 0,
                "time": transaction.updated_at,
                "event_type": event_type,
                "transaction": {
                    "id": transaction.pk,
                    "sender": sender,
                    "recipient": transaction.recipient.profile.tg_name,
                    "recipient_photo": transaction.recipient.profile.get_photo_url(),
                    "amount": transaction.amount,
                    "status": transaction.get_status_display(),
                    "is_anonymous": transaction.is_anonymous,
                    "reason": transaction.reason,
                    "photo": transaction.get_photo_url()
                },
                "scope": event_type.get('scope')
            }
            feed_data.append(event_data)
        return Response(feed_data)
