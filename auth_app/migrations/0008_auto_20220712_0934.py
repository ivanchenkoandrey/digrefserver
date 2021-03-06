# Generated by Django 3.2.12 on 2022-07-12 06:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth_app', '0007_auto_20220629_1422'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='account',
            name='frozen',
        ),
        migrations.AlterField(
            model_name='account',
            name='account_type',
            field=models.CharField(choices=[('I', 'Заработанные'), ('D', 'Для раздачи'), ('F', 'Ожидает подтверждения'), ('S', 'Системный'), ('B', 'Сгоревшие'), ('O', 'Для расчета премий'), ('P', 'Покупки'), ('T', 'Эмитент')], max_length=1, verbose_name='Тип счета'),
        ),
    ]
