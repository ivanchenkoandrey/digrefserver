# Generated by Django 3.2.12 on 2022-09-08 17:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth_app', '0024_auto_20220908_0031'),
    ]

    operations = [
        migrations.AddField(
            model_name='likekind',
            name='code',
            field=models.TextField(null=True, verbose_name='Код Типа Лайка'),
        ),
    ]
