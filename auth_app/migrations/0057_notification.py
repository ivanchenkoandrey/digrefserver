# Generated by Django 3.2.12 on 2022-10-27 14:32

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('auth_app', '0056_fcmtoken_device'),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('L', 'Лайк'), ('C', 'Комментарий'), ('H', 'Челлендж'), ('T', 'Перевод')], max_length=1, verbose_name='Тип уведомления')),
                ('theme', models.CharField(max_length=255, verbose_name='Тема')),
                ('text', models.TextField(verbose_name='Текст')),
                ('read', models.BooleanField(default=False, verbose_name='Прочитано')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Изменено')),
                ('initiated_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='initiatenoties', to=settings.AUTH_USER_MODEL, verbose_name='Инициатор события')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'db_table': 'notifications',
            },
        ),
    ]
