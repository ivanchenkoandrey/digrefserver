from django.contrib import admin

from .models import *


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['tg_id', 'tg_name',
                    'surname', 'first_name']
    list_select_related = ['user']


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization_type']


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['account_type', 'owner', 'organization', 'amount', 'challenge']
    list_select_related = ['owner', 'organization', 'challenge']
    list_filter = ['account_type', 'owner']


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['profile', 'contact_type', 'contact_id', 'confirmed']
    list_select_related = ['profile']
    list_filter = ['contact_type']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['sender', 'recipient', 'created_at', 'updated_at', 'status']
    list_select_related = ['sender', 'recipient']
    list_filter = ['status']


@admin.register(UserStat)
class UserStatAdmin(admin.ModelAdmin):
    list_display = ['user', 'period', 'bonus', 'income_at_start', 'income_at_end']
    list_select_related = ['user', 'period']
    list_filter = ['user', 'period']


@admin.register(Period)
class PeriodAdmin(admin.ModelAdmin):
    list_display = ['start_date', 'end_date', 'name']


@admin.register(TransactionState)
class TransactionStateAdmin(admin.ModelAdmin):
    list_display = ['transaction', 'created_at', 'controller', 'status', 'reason']
    list_select_related = ['transaction', 'controller']
    list_filter = ['status']


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ['user', 'role']
    list_select_related = ['user', 'organization']
    list_filter = ['role']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['content_type', 'object_id', 'content_object', 'user', 'text', 'picture', 'date_created']
    list_select_related = ['user']
    list_filter = ['content_type', 'user']


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ['content_type', 'object_id', 'content_object', 'like_kind', 'user', 'is_liked', 'date_created']
    list_select_related = ['user', 'like_kind']
    list_filter = ['content_type', 'user']


@admin.register(LikeKind)
class LikeKindAdmin(admin.ModelAdmin):
    list_display = ['id', 'code', 'name', 'icon']


@admin.register(LikeStatistics)
class LikeStatisticsAdmin(admin.ModelAdmin):
    list_display = ['content_type', 'object_id', 'content_object', 'like_kind_id', 'last_change_at', 'like_counter']


@admin.register(LikeCommentStatistics)
class LikeCommentStatisticsAdmin(admin.ModelAdmin):
    list_display = ['content_type', 'object_id', 'content_object', 'first_comment_id', 'last_comment_id', 'last_event_comment_id',
                    'comment_counter', 'last_like_or_comment_change_at']


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at', 'updated_at']


@admin.register(ChallengeParticipant)
class ChallengeParticipantAdmin(admin.ModelAdmin):
    pass


@admin.register(ChallengeReport)
class ChallengeReportAdmin(admin.ModelAdmin):
    pass


@admin.register(FCMToken)
class FCMTokenAdmin(admin.ModelAdmin):
    list_display = ['token', 'device', 'user']
    list_select_related = ['user']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'type', 'theme', 'text', 'read', 'updated_at']
    list_select_related = ['user']
    list_filter = ['user', 'type']


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['event_type', 'event_object_id', 'object_selector', 'time', 'scope', 'user']
    list_select_related = ['scope', 'user']
    list_filter = ['object_selector', 'event_type']