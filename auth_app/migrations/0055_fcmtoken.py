# Generated by Django 3.2.12 on 2022-10-25 10:26

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('auth_app', '0054_alter_account_challenge'),
    ]

    operations = [
        migrations.CreateModel(
            name='FCMToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(db_index=True, max_length=255, verbose_name='Токен')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fcmtokens', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'db_table': 'fcm_tokens',
            },
        ),
    ]
