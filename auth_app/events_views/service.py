import logging
from datetime import timedelta

from auth_app.models import EventTypes, Transaction, Profile

logger = logging.getLogger(__name__)

TRANSACTION_FIELDS = (
    "id",
    "sender__profile__tg_name",
    "is_public",
    "recipient__profile__tg_name",
    "recipient__profile__photo",
    "recipient__profile__first_name",
    "recipient__profile__surname",
    "amount",
    "status",
    "is_anonymous",
    "reason",
    "photo",
    "updated_at",
    "like_statistics__like_counter",
    "like_comment_statistics__comment_counter"
)

TRANSACTION_STATUS_DATA = {'A': 'Одобрено', 'R': 'Выполнена'}


def get_event_type(user, recipient, is_public, event_types):
    if is_public is True and recipient != user:
        return event_types.get('Новая публичная транзакция')
    return event_types.get('Входящая транзакция')


def get_events_list(request):
    request_user_tg_name = get_request_user_tg_name(request)
    extended_queryset = get_transactions_queryset(request)
    event_types = get_event_types_data()
    feed_data = []
    for (pk, sender, is_public, recipient_tg_name,
         recipient_photo, recipient_first_name,
         recipient_surname, amount, status,
         is_anonymous, reason, photo,
         updated_at, likes_counter, comments_counter) in extended_queryset:
        event_type = get_event_type(request_user_tg_name, recipient_tg_name, is_public, event_types).to_json()
        sender = 'anonymous' if is_anonymous else sender
        del event_type['record_type']
        event_data = {
            "id": 0,
            "time": updated_at + timedelta(hours=3),
            "event_type": event_type,
            "transaction": {
                "id": pk,
                "sender": sender,
                "recipient": recipient_tg_name,
                "recipient_photo": f"/media/{recipient_photo}" if recipient_photo else None,
                "recipient_first_name": recipient_first_name,
                "recipient_surname": recipient_surname,
                "amount": amount,
                "status": TRANSACTION_STATUS_DATA.get(status),
                "is_anonymous": is_anonymous,
                "reason": reason,
                "photo": f"/media/{photo}" if photo else None,
                "likes_counter": likes_counter,
                "comments_counter": comments_counter
            },
            "scope": event_type.get('scope')
        }
        feed_data.append(event_data)
    return feed_data


def get_event_types_data():
    event_types = {event_type.name: event_type for event_type in EventTypes.objects.all()}
    return event_types


def get_request_user_tg_name(request):
    request_user_tg_name = Profile.objects.filter(user=request.user).only('tg_name').first().tg_name
    return request_user_tg_name


def get_transactions_queryset(request):
    public_transactions = (Transaction.objects
                           .select_related('sender__profile', 'recipient__profile')
                           .prefetch_related('like_statistics', 'like_comment_statistics')
                           .filter(is_public=True, status__in=['A', 'R'])
                           .exclude(recipient=request.user)
                           .values_list(*TRANSACTION_FIELDS))
    transactions_receiver_only = (Transaction.objects
                                  .select_related('sender__profile', 'recipient__profile')
                                  .prefetch_related('like_statistics', 'like_comment_statistics')
                                  .filter(recipient=request.user, status__in=['A', 'R'])
                                  .values_list(*TRANSACTION_FIELDS))
    extended_queryset = (public_transactions.union(transactions_receiver_only)
                         .order_by('-updated_at')[:25])
    return extended_queryset
