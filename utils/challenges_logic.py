from datetime import timedelta
from typing import Dict, List

from django.db.models import Q

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


def update_challenge_photo_link_to_thumbnail(challenges: List[Dict]) -> None:
    for challenge in challenges:
        if photo := challenge.get('photo'):
            link = '/media/{photo}'.format(photo=get_thumbnail_link(photo)).replace("//", "/")
            challenge.update({'photo': link})
        else:
            challenge.update({'photo': None})


def update_challenge_creator_photo_link_to_thumbnail(challenges: List[Dict]) -> None:
    for challenge in challenges:
        if photo := challenge.get('creator_photo'):
            link = '/media/{photo}'.format(photo=get_thumbnail_link(photo)).replace("//", "/")
            challenge.update({'creator_photo': link})
        else:
            challenge.update({'creator_photo': None})


def update_participant_photo_link_to_thumbnail(participants: List[Dict]) -> None:
    for participant in participants:
        if photo := participant.get('participant_photo'):
            link = '/media/{photo}'.format(photo=get_thumbnail_link(photo)).replace("//", "/")
            participant.update({'participant_photo': link})
        else:
            participant.update({'participant_photo': None})


def update_report_photo_link_to_thumbnail(participants: List[Dict]) -> None:
    for participant in participants:
        if photo := participant.get('report_photo'):
            link = '/media/{photo}'.format(photo=get_thumbnail_link(photo)).replace("//", "/")
            participant.update({'report_photo': link})
        else:
            participant.update({'report_photo': None})


def update_challenge_photo_link(challenges: List[Dict]) -> None:
    for challenge in challenges:
        if photo := challenge.get('photo'):
            challenge.update({'photo': f'/media/{photo}'})
        else:
            challenge.update({'photo': None})


def update_participant_photo_link(participants: List[Dict]) -> None:
    for participant in participants:
        if photo := participant.get('participant_photo'):
            participant.update({'participant_photo': f'/media/{photo}'})
        else:
            participant.update({'participant_photo': None})


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


def update_time_in_challenges(challenges: List[Dict]) -> None:
    for challenge in challenges:
        updated_at = challenge.get('updated_at')
        challenge.update({'updated_at': updated_at + timedelta(hours=3)})


def update_time_in_winners_list(winners_list: List[Dict]) -> None:
    for winner in winners_list:
        awarded_at = winner.get('awarded_at')
        winner.update({'awarded_at': awarded_at + timedelta(hours=3)})


def update_time_in_participants_list(participants_list: List[Dict]) -> None:
    for participant in participants_list:
        awarded_at = participant.get('report_created_at')
        participant.update({'report_created_at': awarded_at + timedelta(hours=3)})


def check_if_new_reports_exists(user_id: int) -> bool:
    from auth_app.models import ChallengeReport

    new_reports_exists = (ChallengeReport.objects
                          .filter(Q(challenge__creator_id=user_id) & Q(state__in=['S', 'F', 'R']))
                          .exists())
    return new_reports_exists
