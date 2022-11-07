from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models import (Q, F, Exists, OuterRef, Count,
                              Prefetch, ExpressionWrapper, DateTimeField)


class CustomChallengeQueryset(models.QuerySet):
    def get_challenges_list(self, user_id):
        from auth_app.models import ChallengeReport

        return (self.select_related('creator__profile').prefetch_related(
            Prefetch('reports', queryset=ChallengeReport.objects.select_related('participant__user_participant')))
                .annotate(approved_reports_amount=Count('reports', filter=Q(reports__state__in=['A', 'W'])),
                          is_new_reports=Exists(
                              ChallengeReport.objects.filter(
                                  Q(challenge_id=OuterRef('pk')) &
                                  Q(challenge__creator_id=user_id) &
                                  Q(state__in=['S', 'F', 'R']))
                          )
                          )
                .only('id', 'name', 'photo', 'updated_at', 'states', 'approved_reports_amount', 'description',
                      'start_balance', 'creator_id', 'parameters', 'is_new_reports', 'winners_count',
                      'creator__profile__first_name', 'creator__profile__surname', 'creator__profile__organization_id',
                      'creator__profile__photo', 'creator__profile__tg_name', 'end_at')
                .order_by('-pk'))

    def get_all_challenges(self, user_id):
        return self.get_challenges_list(user_id).values(
            'id', 'name', 'photo', 'updated_at', 'states', 'approved_reports_amount',
            'creator_id', 'parameters', 'winners_count', 'is_new_reports', fund=F('start_balance')
        ).distinct().order_by('-pk')

    def get_active_only(self, user_id):
        return (self.get_challenges_list(user_id)
        .filter(~Q(states__contains=['C'])).values(
            'id', 'name', 'photo', 'updated_at', 'states', 'approved_reports_amount',
            'creator_id', 'parameters', 'is_new_reports', fund=F('start_balance')
        )).distinct().order_by('-pk')

    def get_challenge_by_pk(self, user_id, pk):
        return (self.get_challenges_list(user_id)
                .filter(pk=pk)).values(
            'id', 'name', 'photo', 'updated_at', 'states', 'approved_reports_amount', 'description',
            'creator_id', 'parameters', 'is_new_reports', 'winners_count', 'end_at',
            creator_organization_id=F('creator__profile__organization_id'), fund=F('start_balance'),
            creator_name=F('creator__profile__first_name'), creator_surname=F('creator__profile__surname'),
            creator_photo=F('creator__profile__photo'), creator_tg_name=F('creator__profile__tg_name')
        ).distinct().order_by('-pk')


class CustomChallengeParticipantQueryset(models.QuerySet):
    def get_total_received_points(self, user, challenge_id):
        return (self.filter(user_participant=user, challenge_id=challenge_id)
                .only('total_received').values('total_received'))

    def get_winners_data(self, challenge_id):
        return (self.select_related('user_participant__profile')
                .prefetch_related('challengereports')
                .filter(Q(challengereports__state='W') & Q(challenge_id=challenge_id))
                .only('user_participant__id',
                      'user_participant__profile__photo',
                      'user_participant__profile__first_name',
                      'user_participant__profile__surname',
                      'user_participant__profile__tg_name',
                      'nickname',
                      'challengereports__updated_at',
                      'total_received')
                .values('nickname',
                        'total_received',
                        participant_tg_name=F('user_participant__profile__tg_name'),
                        participant_id=F('user_participant__id'),
                        participant_photo=F('user_participant__profile__photo'),
                        participant_name=F('user_participant__profile__first_name'),
                        participant_surname=F('user_participant__profile__surname'),
                        awarded_at=F('challengereports__updated_at')
                        ))

    def get_contenders_data(self, challenge_id):
        return (self.select_related('user_participant__profile')
                .prefetch_related('challengereports')
                .annotate(reports_count=Count('challengereports',
                                              filter=Q(challengereports__state__in=['S', 'F', 'R'])))
                .filter(challenge_id=challenge_id, reports_count__gt=0)
                .only('user_participant__id',
                      'user_participant__profile__photo',
                      'user_participant__profile__first_name',
                      'user_participant__profile__surname',
                      'nickname',
                      'challengereports__created_at',
                      'challengereports__text',
                      'challengereports__photo',
                      'challengereports__id'
                      )
                .values('nickname',
                        participant_id=F('user_participant__id'),
                        participant_photo=F('user_participant__profile__photo'),
                        participant_name=F('user_participant__profile__first_name'),
                        participant_surname=F('user_participant__profile__surname'),
                        report_created_at=F('challengereports__created_at'),
                        report_text=F('challengereports__text'),
                        report_photo=F('challengereports__photo'),
                        report_id=F('challengereports__id')))


class CustomChallengeReportQueryset(models.QuerySet):
    def get_user_challenge_result_data(self, user, challenge_id):
        return (self.select_related('participant').filter(challenge_id=challenge_id, participant__user_participant=user)
                .only('updated_at', 'text', 'photo', 'participant__total_received', 'state')
                .values('updated_at', 'text', 'photo', status=F('state'), received=F('participant__total_received')))

    def get_winners_reports_by_challenge_id(self, challenge_id):
        return (self.select_related('participant__user_participant__profile', 'challenge')
                .filter(challenge_id=challenge_id, state='W')
                .only('id', 'participant__nickname', 'updated_at', 'photo',
                      'challenge_id',
                      'participant__user_participant__id',
                      'participant__user_participant__profile__first_name',
                      'participant__user_participant__profile__surname',
                      'participant__user_participant__profile__tg_name',
                      'participant__user_participant__profile__photo'))


class CustomTransactionQueryset(models.QuerySet):
    """
    Объект, инкапсулирующий в себе логику кастомных запросов к БД
    в рамках менеджера objects в инстансах модели Transaction
    """

    def filter_by_user(self, current_user):
        """
        Возвращает список транзакций пользователя
        """
        queryset = (self
                    .select_related('sender__profile', 'recipient__profile', 'reason_def',
                                    'sender_account__owner__profile',
                                    'recipient_account__owner__profile', 'from_challenge',
                                    'to_challenge')
                    .prefetch_related('_objecttags')
                    .filter((Q(sender=current_user) | (Q(recipient=current_user) & ~(Q(status__in=['G', 'C', 'D']))) |
                             (Q(transaction_class='H') & Q(sender_account__owner=current_user)) |
                             (Q(transaction_class__in=['W', 'F']) & Q(recipient_account__owner=current_user)))))
        return self.add_expire_to_cancel_field(queryset).order_by('-updated_at')

    def filter_by_user_limited(self, user, offset, limit):
        return self.filter_by_user(user)[offset * limit: offset * limit + limit]

    def filter_by_user_sent_only(self, user, offset, limit):
        return (self.filter_by_user(user).filter(Q(sender=user) |
                                                 (Q(transaction_class='H') & Q(sender_account__owner=user)))
                [offset * limit: offset * limit + limit])

    def filter_by_user_received_only(self, user, offset, limit):
        return (self.filter_by_user(user).filter(
            (Q(recipient=user) & ~(Q(status__in=['G', 'C', 'D']))) |
            (Q(transaction_class__in=['W', 'F']) & Q(recipient_account__owner=user)))
            [offset * limit: offset * limit + limit])

    def filter_to_use_by_controller(self):
        """
        Возвращает список транзакций со статусом 'Ожидает подтверждения'
        """
        queryset = (self
                    .select_related('sender__profile', 'recipient__profile', 'reason_def',
                                    'sender_account__owner__profile',
                                    'recipient_account__owner__profile')
                    .prefetch_related('_objecttags')
                    .filter(status='W'))
        return self.add_expire_to_cancel_field(queryset).order_by('-created_at')

    def filter_by_period(self, current_user, period_id):
        """
        Возвращает список транзакций пользователя, совершенных в рамках конкретного периода
        """
        queryset = self.filter_by_user(current_user).filter(period_id=period_id)
        return self.add_expire_to_cancel_field(queryset).order_by('-updated_at')

    def feed_version(self, user):
        from auth_app.models import Like

        queryset = self.annotate(last_like_comment_time=F(
            'like_comment_statistics__last_like_or_comment_change_at'),

            user_liked=Exists(Like.objects.filter(
                Q(object_id=OuterRef('pk'),
                  like_kind__code='like',
                  user_id=user.id,
                  is_liked=True))),

            user_disliked=Exists(Like.objects.filter(
                Q(object_id=OuterRef('pk'),
                  like_kind__code='dislike',
                  user_id=user.id,
                  is_liked=True)
            )))

        return queryset

    @staticmethod
    def add_expire_to_cancel_field(queryset):
        """
        Возвращает список транзакций, к которому добавлено поле формата даты, где указывается,
        когда истекает возможность отменить транзакцию со стороны пользователя
        """
        return queryset.annotate(expire_to_cancel=ExpressionWrapper(
            F('created_at') + timedelta(seconds=settings.GRACE_PERIOD), output_field=DateTimeField()))


class CustomLikeQueryset(models.QuerySet):
    """
    Объект, инкапсулирующий в себе логику кастомных запросов к БД
    в рамках менеджера objects в инстансах модели Comment
    """

    def filter_by_transaction(self, transaction):
        """
        Возвращает список комментариев заданной транзакции
        """
        return self.filter(transaction=transaction, is_liked=True)

    def filter_by_transaction_and_like_kind(self, transaction, like_kind):
        """
        Возвращает список комментариев заданной транзакции и типа лайка
        """
        return self.filter(transaction=transaction, like_kind=like_kind, is_liked=True)

    def filter_by_user(self, user):
        """
        Возвращает список комментариев заданного пользователя
        """
        return self.filter(user=user, is_liked=True)

    def filter_by_user_and_like_kind(self, user, like_kind):
        """
        Возвращает список комментариев заданного пользователя и типа лайка
        """
        return self.filter(user=user, like_kind=like_kind, is_liked=True)


class CustomCommentQueryset(models.QuerySet):
    """
    Объект, инкапсулирующий в себе логику кастомных запросов к БД
    в рамках менеджера objects в инстансах модели Comment
    """

    def filter_by_object(self, content_type, object_id):
        """
        Возвращает список комментариев по заданной модели и его айди
        """
        return self.filter(content_type=content_type, object_id=object_id)
