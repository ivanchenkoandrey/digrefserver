import logging
from datetime import timedelta

from django.db.models import F

from auth_app.models import EventTypes, Transaction, Profile, LikeCommentStatistics, LikeStatistics
from utils.thumbnail_link import get_thumbnail_link
from utils.query_debugger import query_debugger

logger = logging.getLogger(__name__)

TRANSACTION_FIELDS = (
    "id",
    "sender_id",
    "sender__profile__tg_name",
    "is_public",
    "recipient_id",
    "recipient__profile__tg_name",
    "recipient__profile__photo",
    "recipient__profile__first_name",
    "recipient__profile__surname",
    "amount",
    "status",
    "is_anonymous",
    "reason",
    "photo",
    "updated_at"
)

TRANSACTION_STATUS_DATA = {'A': 'Одобрено', 'R': 'Выполнена'}


def get_event_type(user, recipient, is_public, event_types):
    if is_public is True and recipient != user:
        return event_types.get('Новая публичная транзакция')
    return event_types.get('Входящая транзакция')


@query_debugger
def get_events_list(request):
    request_user_tg_name = get_request_user_tg_name(request)
    transactions_tuple = get_transactions_queryset(request)
    event_types = get_event_types_data()
    feed_data = []
    comment_statistics = [(statistics.transaction_id, statistics.comment_counter) for statistics in LikeCommentStatistics.objects.
                          select_related('transaction').only('transaction__id', 'comment_counter')]
    like_statistics = [(statistics.transaction_id, statistics.like_kind_id, statistics.like_kind.code, statistics.like_counter, statistics.last_change_at)
                       for statistics in LikeStatistics.objects.select_related('transaction', 'like_kind').
                       only('transaction__id', 'like_kind__id', 'like_kind__code', 'like_counter', 'last_change_at').
                       order_by('last_change_at')]
    for _transaction in transactions_tuple:

        recipient_tg_name = _transaction.recipient.profile.tg_name
        is_public = _transaction.is_public
        sender = _transaction.sender.profile.tg_name
        recipient_photo = _transaction.recipient.profile.photo
        event_type = get_event_type(request_user_tg_name, recipient_tg_name, is_public, event_types).to_json()
        sender = 'anonymous' if _transaction.is_anonymous else sender
        del event_type['record_type']
        transaction_info = {
                "id": _transaction.pk,
                "sender_id": None if _transaction.is_anonymous else _transaction.sender_id,
                "sender": sender,
                "recipient_id": _transaction.recipient_id,
                "recipient": recipient_tg_name,
                "recipient_photo": f"{get_thumbnail_link(recipient_photo.url)}" if recipient_photo else None,
                "recipient_first_name": _transaction.recipient.profile.first_name,
                "recipient_surname": _transaction.recipient.profile.surname,
                "amount": _transaction.amount,
                "status": TRANSACTION_STATUS_DATA.get(_transaction.status),
                "is_anonymous": _transaction.is_anonymous,
                "reason": _transaction.reason,
                "photo": f"{get_thumbnail_link(_transaction.photo.url)}" if _transaction.photo else None,
                "updated_at": _transaction.updated_at,
                "tags": _transaction._objecttags.values("tag_id", name=F("tag__name"))
            }
        comment_statistics_exists = False
        for i in range(len(comment_statistics)):
            if _transaction.id == comment_statistics[i][0]:

                transaction_info['comments'] = comment_statistics[i][1]
                comment_statistics_exists = True
        if not comment_statistics_exists:
            transaction_info['comments'] = 0

        like_statistics_exists = False
        like_info = []
        for i in range(len(like_statistics)):
            if _transaction.id == like_statistics[i][0]:
                like_info.append({'id': like_statistics[i][1], 'code': like_statistics[i][2], 'counter': like_statistics[i][3]})
                transaction_info['last_like'] = like_statistics[i][4]
                like_statistics_exists = True
        transaction_info['reactions'] = like_info

        if not like_statistics_exists:
            transaction_info['last_like'] = None

            # TODO change to "for like_kind in like_kinds...counter=0"
            transaction_info['reactions'] = [{'id': 3, 'code': "Like", 'counter': 0},
                                             {'id': 4, 'code': "Dislike", 'counter': 0}]
        event_data = {
            "id": 0,
            "time": _transaction.updated_at + timedelta(hours=3),
            "event_type": event_type,
            "transaction": transaction_info,
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
                           .prefetch_related('_objecttags')
                           .filter(is_public=True, status__in=['A', 'R'])
                           .exclude(recipient=request.user)
                           .only(*TRANSACTION_FIELDS))
    transactions_receiver_only = (Transaction.objects
                                  .select_related('sender__profile', 'recipient__profile')
                                  .prefetch_related('_objecttags')
                                  .filter(recipient=request.user, status__in=['A', 'R'])
                                  .defer('transaction_class', 'grace_timeout', 'organization_id', 'period', 'scope'))
    extended_transactions = (public_transactions | transactions_receiver_only).distinct().order_by('-updated_at')[:20]
    return extended_transactions
