# Generated by Django 3.2.12 on 2022-11-16 07:47

import django.contrib.postgres.fields.citext
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('auth_app', '0064_challenge_organization'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='tg_id',
            field=django.contrib.postgres.fields.citext.CICharField(blank=True, max_length=20, null=True, verbose_name='Идентификатор пользователя Telegram'),
        ),
    ]
