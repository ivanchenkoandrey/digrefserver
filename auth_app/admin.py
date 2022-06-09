from django.contrib import admin

from .models import (Profile, Organization, Account,
                     Contact, Transaction, UserStat,
                     Period)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_select_related = ['user']


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    pass


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    pass


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['sender', 'recipient', 'created_at', 'updated_at', 'status']
    list_select_related = ['sender', 'recipient']


@admin.register(UserStat)
class UserStatAdmin(admin.ModelAdmin):
    pass


@admin.register(Period)
class PeriodAdmin(admin.ModelAdmin):
    pass
