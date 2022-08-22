from django.contrib import admin

from .models import (Profile, Organization, Account,
                     Contact, Transaction, UserStat,
                     Period, TransactionState, UserRole)


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
    list_display = ['account_type', 'owner', 'organization', 'amount']
    list_select_related = ['owner', 'organization']
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
