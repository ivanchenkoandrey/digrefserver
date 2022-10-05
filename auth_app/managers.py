from django.db import models
from django.db.models import Q, F, Exists, OuterRef, Count, When, Value, Case


class CustomChallengeQueryset(models.QuerySet):
    def get_challenges_list(self, user_id):
        from auth_app.models import ChallengeReport

        return (self.select_related('creator__profile').prefetch_related('reports')
                .annotate(approved_reports_amount=Count('reports', filter=Q(reports__state__in=['A', 'W'])),
                          status=Case(
                              When(Q(creator_id=user_id),
                                   then=Value('Вы создатель челленджа')),
                              When(Q(reports__participant__pk=user_id) & Q(reports__state__in=['S', 'F', 'R']),
                                   then=Value('Отчёт отправлен')),
                              When(Q(reports__participant__pk=user_id) & Q(reports__state__exact='A'),
                                   then=Value('Отчёт подтверждён')),
                              When(Q(reports__participant__pk=user_id) & Q(reports__state__exact='D'),
                                   then=Value('Отчёт отклонён')),
                              When(Q(reports__participant__pk=user_id) & Q(reports__state__exact='W'),
                                   then=Value('Получено вознаграждение')),
                              default=Value('Можно отправить отчёт')
                          ),
                          is_new_reports=Exists(
                              ChallengeReport.objects.filter(
                                  Q(challenge_id=OuterRef('pk')) &
                                  Q(challenge__creator_id=user_id) &
                                  Q(state__in=['S', 'F', 'R']))
                          )
                          
                          )
                .only('id', 'name', 'photo', 'updated_at', 'states', 'approved_reports_amount', 'description',
                      'start_balance', 'creator_id', 'status', 'parameters', 'is_new_reports', 'winners_count',
                      'creator__profile__first_name', 'creator__profile__surname', 'creator__profile__organization_id',
                      'creator__profile__photo', 'creator__profile__tg_name', 'end_at')
                .order_by('-pk'))

    def get_all_challenges(self, user_id):
        return self.get_challenges_list(user_id).values(
            'id', 'name', 'photo', 'updated_at', 'states', 'approved_reports_amount',
            'creator_id', 'status', 'parameters', 'winners_count', 'is_new_reports', fund=F('start_balance')
        )

    def get_active_only(self, user_id):
        return (self.get_challenges_list(user_id)
                .filter(~Q(states__contains=['C'])).values(
            'id', 'name', 'photo', 'updated_at', 'states', 'approved_reports_amount',
            'creator_id', 'status', 'parameters', 'is_new_reports', fund=F('start_balance')
        ))

    def get_challenge_by_pk(self, user_id, pk):
        return (self.get_challenges_list(user_id)
                .filter(pk=pk)).values(
            'id', 'name', 'photo', 'updated_at', 'states', 'approved_reports_amount', 'description',
            'creator_id', 'status', 'parameters', 'is_new_reports', 'winners_count', 'end_at',
            creator_organization_id=F('creator__profile__organization_id'), fund=F('start_balance'),
            creator_name=F('creator__profile__first_name'), creator_surname=F('creator__profile__surname'),
            creator_photo=F('creator__profile__photo'), creator_tg_name=F('creator__profile__tg_name')
        )


class CustomChallengeParticipantQueryset(models.QuerySet):
    def get_winners_data(self, challenge_id):
        return (self.select_related('user_participant__profile')
                .prefetch_related('challengereports')
                .filter(Q(challengereports__state='W') & Q(challenge_id=challenge_id))
                .only('user_participant__id',
                      'user_participant__profile__photo',
                      'user_participant__profile__first_name',
                      'user_participant__profile__surname',
                      'challengereports__updated_at')
                .values(participant_id=F('user_participant__id'),
                        participant_photo=F('user_participant__profile__photo'),
                        participant_name=F('user_participant__profile__first_name'),
                        participant_surname=F('user_participant__profile__surname'),
                        awarded_at=F('challengereports__updated_at')
                        ))

    def get_participants_data(self, challenge_id):
        return (self.select_related('user_participant__profile')
                .prefetch_related('challengereports')
                .filter(challenge_id=challenge_id)
                .only('user_participant__id',
                      'user_participant__profile__photo',
                      'user_participant__profile__first_name',
                      'user_participant__profile__surname',
                      'challengereports__created_at',
                      'challengereports__text',
                      'challengereports__photo',
                      'challengereports__id'
                      )
                .values(participant_id=F('user_participant__id'),
                        participant_photo=F('user_participant__profile__photo'),
                        participant_name=F('user_participant__profile__first_name'),
                        participant_surname=F('user_participant__profile__surname'),
                        report_created_at=F('challengereports__created_at'),
                        report_text=F('challengereports__text'),
                        report_photo=F('challengereports__photo'),
                        report_id=F('challengereports__id')))
