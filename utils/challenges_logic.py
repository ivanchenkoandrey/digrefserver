from datetime import timedelta
from typing import Dict, List

from django.db.models import Q, QuerySet

from auth_app.models import ChallengeReport, Transaction
from utils.thumbnail_link import get_thumbnail_link

MODES = {
    'O': 'От имени организации',
    'U': 'От имени пользователя',
    'P': 'Является публичным',
    'C': 'Является командным',
    'R': 'Нужна регистрация',
    'G': 'Нужна картинка',
    'M': 'Запрет комментариев',
    'E': 'Разрешить комментарии только для участников',
    'L': 'Лайки запрещены',
    'T': 'Разрешить лайки только для участников',
    'X': 'Комментарии отчетов разрешены только автору отчета, организатору и судьям',
    'W': 'Комментарии отчетов разрешены только участникам',
    'I': 'Лайки отчетов разрешены только участникам',
    'N': 'Участник может использовать никнейм',
    'H': 'Участник может сделать отчёт приватным',
    'A': 'Отчеты анонимизированы до подведения итогов, не видны ни имена пользователей, ни псевдонимы',
    'Q': 'Участник может рассылать приглашения',
    'Y': 'Подтверждение будет выполняться судейской коллегией (через выдачу ими баллов)'
}

CHALLENGE_REPORT_STATES = {
    'S': 'Направлен организатору для подтверждения',
    'F': 'В процессе оценки судьями',
    'A': 'Подтверждено',
    'D': 'Отклонено',
    'R': 'Повторно направлено организатору',
    'W': 'Получено вознаграждение'
}


def reconfigure_challenges_queryset_into_dictionary(challenges: QuerySet, pk=False) -> List[Dict]:
    challenges_list = []
    for challenge in challenges:
        comments_amount = challenge.comments_amount
        likes_amount = challenge.likes_amount
        data = {
            'id': challenge.id,
            'user_liked': challenge.user_liked,
            'likes_amount': likes_amount if likes_amount is not None else 0,
            'comments_amount': comments_amount if comments_amount is not None else 0,
            'name': challenge.name,
            'photo': challenge.photo.name,
            'updated_at': challenge.updated_at,
            'states': challenge.states,
            'approved_reports_amount': challenge.approved_reports_amount,
            'creator_id': challenge.creator_id,
            'creator_name': challenge.first_name,
            'creator_surname': challenge.surname,
            'parameters': challenge.parameters,
            'winners_count': challenge.winners_count,
            'is_new_reports': challenge.is_new_reports,
            'fund': challenge.fund,
            'status': '' if challenge.status is None else challenge.status
        }
        if pk:
            data.update({
                "end_at": challenge.end_at,
                "creator_name": challenge.first_name,
                "creator_organization_id": challenge.organization_pk,
                "creator_photo": challenge.profile_photo,
                "creator_surname": challenge.surname,
                "creator_tg_name": challenge.tg_name,
                "description": challenge.description
            })
        challenges_list.append(data)
    return challenges_list


def add_annotated_fields_to_challenges(challenges: List[Dict]) -> None:
    for challenge in challenges:
        parameters = challenge.get('parameters')
        if parameters:
            parameters = sorted(parameters, key=lambda obj: obj['id'])
            challenge.update(
                {'prize_size': parameters[0]['value'],
                 'awardees': parameters[1]['value']})


def get_challenge_state_values(challenges: List[Dict]) -> None:
    for challenge in challenges:
        for index, state in enumerate(states := challenge.get('states')):
            states[index] = MODES.get(state)


def update_photo_link(data: List[Dict], field: str) -> None:
    for item in data:
        if photo := item.get(field):
            item.update({field: f'/media/{photo}'})
        else:
            item.update({field: None})


def update_link_on_thumbnail(data: List[Dict], field: str) -> None:
    for item in data:
        if photo := item.get(field):
            link = '/media/{photo}'.format(photo=get_thumbnail_link(photo)).replace("//", "/")
            item.update({field: link})
        else:
            item.update({field: None})


def set_active_field(challenges: List[Dict]) -> None:
    for challenge in challenges:
        if 'C' not in challenge.get('states'):
            challenge.update({'active': True})
        else:
            challenge.update({'active': False})


def set_completed_field(challenges: List[Dict]) -> None:
    for challenge in challenges:
        if 'C' in challenge.get('states'):
            challenge.update({'completed': True})
        else:
            challenge.update({'completed': False})


def calculate_remaining_top_places(challenges: List[Dict]) -> None:
    for challenge in challenges:
        parameters = challenge.get('parameters')
        if parameters:
            parameters = sorted(parameters, key=lambda obj: obj['id'])
            winners_count = challenge.get('winners_count')
            prizes = parameters[1]['value']
            challenge.update({'remaining_top_places': prizes - winners_count})
        else:
            challenge.update({'remaining_top_places': None})


def update_time(data: List[Dict], field: str) -> None:
    for item in data:
        awarded_at = item.get(field)
        item.update({field: awarded_at + timedelta(hours=3)})


def check_if_new_reports_exists(user_id: int) -> bool:
    from auth_app.models import ChallengeReport

    new_reports_exists = (ChallengeReport.objects
                          .filter(Q(challenge__creator_id=user_id) & Q(state__in=['S', 'F', 'R']))
                          .exists())
    return new_reports_exists


def set_names_to_null(participants: List[Dict]) -> None:
    for participant in participants:
        if participant.get('nickname') is not None:
            participant.update({'participant_name': None, 'participant_surname': None})


def get_challenge_report_status(state: str) -> str:
    return CHALLENGE_REPORT_STATES.get(state)


def set_winner_nickname(winners: List[Dict]) -> None:
    for winner in winners:
        if winner.get('nickname') is None:
            winner['nickname'] = winner.get('participant_tg_name')
        del winner['participant_tg_name']


def get_reports_data_from_queryset(reports: QuerySet[ChallengeReport]) -> List[Dict]:
    reports_list = []
    for report in reports:
        participant_photo = report.participant.user_participant.profile.get_photo_url()
        report_photo = report.get_photo_url
        report_data = {
            "id": report.pk,
            "nickname": report.participant.nickname,
            "awarded_at": report.updated_at,
            "photo": get_thumbnail_link(report_photo) if report_photo is not None else None,
            "challenge_id": report.challenge_id,
            "participant_id": report.participant.user_participant_id,
            "participant_tg_name": report.participant.user_participant.profile.tg_name,
            "participant_name": report.participant.user_participant.profile.first_name,
            "participant_surname": report.participant.user_participant.profile.surname,
            "participant_photo": get_thumbnail_link(participant_photo) if participant_photo is not None else None
        }
        reports_list.append(report_data)
    return reports_list


def add_transaction_amount_for_winner_reports(reports):
    reports_ids = [report.get('id') for report in reports]
    transactions = {transaction.challenge_report_id: transaction.amount
                    for transaction in (Transaction.objects
                                        .filter(challenge_report_id__in=reports_ids)
                                        .only('challenge_report_id', 'amount'))}

    for report in reports:
        report_id = report.get('id')
        award = transactions.get(report_id)
        report.update({"award": int(award) if award else None})
