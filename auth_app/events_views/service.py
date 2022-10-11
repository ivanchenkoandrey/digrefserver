import logging
from datetime import timedelta
from typing import List, Dict

from django.db.models import F

from auth_app.models import EventTypes, Transaction, Profile, Event, Challenge, ChallengeReport
from utils.challenges_logic import update_link_on_thumbnail, update_time
from utils.thumbnail_link import get_thumbnail_link

logger = logging.getLogger(__name__)

event_types_data = {event_type.name: event_type.to_json() for event_type in EventTypes.objects.all()}

TRANSACTION_TYPE_ID = event_types_data.get('Новая публичная транзакция').get('id')
WINNER_TYPE_ID = event_types_data.get('Новый победитель челленджа').get('id')
CHALLENGE_TYPE_ID = event_types_data.get('Создан челлендж').get('id')

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


def get_events_list(request, offset, limit):
    request_user_tg_name = get_request_user_tg_name(request)
    transactions = get_transactions_queryset(request, offset, limit)
    event_types = get_event_types_data()
    feed_data = []
    for _transaction in transactions:
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
            "tags": _transaction._objecttags.values("tag_id", name=F("tag__name")),
            "comments_amount": _transaction.comments_amount,
            "last_like_comment_time": _transaction.last_like_comment_time,
            "user_liked": _transaction.user_liked,
            "user_disliked": _transaction.user_disliked,
            "reactions": _transaction.like_statistics.values('id', code=F('like_kind__code'),
                                                             counter=F('like_counter'))
        }
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


def get_transactions_queryset(request, offset, limit):
    public_transactions = (Transaction.objects
                           .select_related('sender__profile', 'recipient__profile')
                           .prefetch_related('_objecttags', 'likes',
                                             'like_statistics', 'like_comment_statistics')
                           .filter(is_public=True, status__in=['A', 'R'])
                           .exclude(recipient=request.user)
                           .feed_version(request.user)
                           .only(*TRANSACTION_FIELDS))
    transactions_receiver_only = (Transaction.objects
                                  .select_related('sender__profile', 'recipient__profile')
                                  .prefetch_related('_objecttags', 'likes',
                                                    'like_statistics', 'like_comment_statistics')
                                  .filter(recipient=request.user, status__in=['A', 'R'])
                                  .feed_version(request.user)
                                  .defer('transaction_class', 'grace_timeout', 'organization_id', 'period', 'scope'))

    extended_transactions = ((public_transactions | transactions_receiver_only)
                             .distinct('updated_at', 'id')
                             .order_by('-updated_at')[offset * limit:offset * limit + limit])
    return extended_transactions


def get_events_data(offset, limit):
    events = {event.id: event.to_json() for event in
              Event.objects.order_by('-time')[offset * limit: offset * limit + limit]}
    events_data = []
    transaction_event_pairs = get_event_objects_pairs(events, TRANSACTION_TYPE_ID)
    transactions = get_transactions_from_events(list(transaction_event_pairs.keys()))
    for tr in transactions:
        transaction_event_pairs.get(tr.get('id')).update({'transaction': tr})
    winners_event_pairs = get_event_objects_pairs(events, WINNER_TYPE_ID)
    winners = get_winners_from_events(list(winners_event_pairs.keys()))
    for w in winners:
        winners_event_pairs.get(w.get('id')).update({'winner': w})
    challenge_event_pairs = get_event_objects_pairs(events, CHALLENGE_TYPE_ID)
    challenges = get_challenges_from_events(list(challenge_event_pairs.keys()))
    for ch in challenges:
        challenge_event_pairs.get(ch.get('id')).update({'challenge': ch})
    for tr in transaction_event_pairs.values():
        events_data.append(tr)
    for w in winners_event_pairs.values():
        events_data.append(w)
    for ch in challenge_event_pairs.values():
        events_data.append(ch)
    update_time(events_data, 'time')
    return sorted(events_data, key=lambda item: item['time'], reverse=True)


def get_event_objects_pairs(events: Dict[int, Dict], type_id: int) -> Dict[int, Dict]:
    return {event['event_object_id']: event
            for event in events.values() if event['event_type_id'] == type_id}


def get_transactions_from_events(transaction_id_array: List[int]) -> Dict:
    transactions = (Transaction.objects
                    .select_related('sender__profile', 'recipient__profile')
                    .prefetch_related('_objecttags')
                    .filter(pk__in=transaction_id_array)
                    .only('sender__profile__tg_name',
                          'sender_id',
                          'recipient_id',
                          'recipient__profile__tg_name',
                          'recipient__profile__photo',
                          'amount',
                          'updated_at',
                          'is_anonymous',
                          'id')
                    .values('id', 'amount', 'updated_at', 'sender_id',
                            'recipient_id', 'is_anonymous',
                            sender_tg_name=F('sender__profile__tg_name'),
                            recipient_tg_name=F('recipient__profile__tg_name'),
                            recipient_photo=F('recipient__profile__photo')))
    update_link_on_thumbnail(transactions, 'recipient_photo')
    update_time(transactions, 'updated_at')
    for tr in transactions:
        if tr.get('is_anonymous'):
            tr.update({'sender_id': None, 'sender_tg_name': None})
    return transactions


def get_challenges_from_events(challenge_id_array: List[int]) -> Dict:
    challenges = (Challenge.objects
                  .select_related('creator__profile')
                  .filter(pk__in=challenge_id_array)
                  .only('photo', 'created_at', 'name', 'end_at',
                        'creator_id', 'id',
                        'creator__profile__first_name',
                        'creator__profile__surname',
                        'creator__profile__tg_name'
                        )
                  .values('id', 'photo', 'created_at', 'name', 'creator_id',
                          creator_first_name=F('creator__profile__first_name'),
                          creator_surname=F('creator__profile__surname'),
                          creator_tg_name=F('creator__profile__tg_name')))
    update_link_on_thumbnail(challenges, 'photo')
    update_time(challenges, 'created_at')
    return challenges


def get_winners_from_events(winners_id_array: List[int]) -> Dict:
    winners = (ChallengeReport.objects
               .select_related('challenge__organized_by',
                               'participant__user_participant__profile')
               .filter(pk__in=winners_id_array)
               .only('id', 'updated_at', 'challenge__name',
                     'challenge_id', 'challenge__creator_id',
                     'participant__user_participant_id',
                     'participant__user_participant__profile__first_name',
                     'participant__user_participant__profile__surname',
                     'participant__user_participant__profile__tg_name',
                     'participant__user_participant__profile__photo')
               .values('id', 'updated_at', challenge_name=F('challenge__name'),
                       winner_id=F('participant__user_participant_id'),
                       winner_first_name=F('participant__user_participant__profile__first_name'),
                       winner_surname=F('participant__user_participant__profile__surname'),
                       winner_tg_name=F('participant__user_participant__profile__tg_name'),
                       winner_photo=F('participant__user_participant__profile__photo')))
    return winners
