# Generated by Django 3.2.12 on 2022-08-12 09:53

from django.conf import settings
import django.contrib.postgres.fields.citext
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('auth_app', '0009_auto_20220804_1920'),
    ]

    operations = [
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_object_id', models.IntegerField(blank=True, null=True)),
                ('event_record_id', models.IntegerField(blank=True, null=True)),
                ('time', models.DateTimeField(verbose_name='Время события')),
            ],
            options={
                'db_table': 'events',
            },
        ),
        migrations.CreateModel(
            name='EventTypes',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', django.contrib.postgres.fields.citext.CITextField()),
                ('object_type', models.CharField(blank=True, choices=[('T', 'Транзакция'), ('Q', 'Запрос (челлендж, квест)')], max_length=1, null=True, verbose_name='Тип объекта')),
                ('record_type', models.CharField(blank=True, choices=[('S', 'Статус транзакции'), ('L', 'Лайк'), ('C', 'Комментарий')], max_length=1, null=True, verbose_name='Тип записи о событии')),
                ('is_personal', models.BooleanField(verbose_name='Относится к пользователю')),
                ('has_scope', models.BooleanField(verbose_name='Имеет область видимости')),
            ],
            options={
                'db_table': 'event_types',
            },
        ),
        migrations.DeleteModel(
            name='Setting',
        ),
        migrations.AddField(
            model_name='period',
            name='organization',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='periods', to='auth_app.organization', verbose_name='Организация'),
        ),
        migrations.AddField(
            model_name='transaction',
            name='grace_timeout',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Время окончания периода возможной отмены'),
        ),
        migrations.AddField(
            model_name='transaction',
            name='is_anonymous',
            field=models.BooleanField(blank=True, null=True, verbose_name='Отправитель скрыт'),
        ),
        migrations.AddField(
            model_name='transaction',
            name='is_public',
            field=models.BooleanField(blank=True, null=True, verbose_name='Публичность'),
        ),
        migrations.AddField(
            model_name='transaction',
            name='organization',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='organization_public_transactions', to='auth_app.organization', verbose_name='Согласующая организация'),
        ),
        migrations.AddField(
            model_name='transaction',
            name='period',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='auth_app.period', verbose_name='Период'),
        ),
        migrations.AddField(
            model_name='transaction',
            name='scope',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='scope_public_transactions', to='auth_app.organization', verbose_name='Уровень публикации'),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='status',
            field=models.CharField(choices=[('W', 'Ожидает подтверждения'), ('A', 'Одобрено'), ('D', 'Отклонено'), ('G', 'Ожидает'), ('R', 'Выполнена'), ('C', 'Отменена')], max_length=1, verbose_name='Состояние транзакции'),
        ),
        migrations.AlterField(
            model_name='transactionstate',
            name='status',
            field=models.CharField(choices=[('W', 'Ожидает подтверждения'), ('A', 'Одобрено'), ('D', 'Отклонено'), ('G', 'Ожидает'), ('R', 'Выполнена'), ('C', 'Отменена')], max_length=1, verbose_name='Состояние транзакции'),
        ),
        migrations.AddField(
            model_name='event',
            name='event_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='auth_app.eventtypes', verbose_name='Тип события'),
        ),
        migrations.AddField(
            model_name='event',
            name='scope',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='auth_app.organization', verbose_name='Область видимости'),
        ),
        migrations.AddField(
            model_name='event',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='Пользователь'),
        ),
    ]
