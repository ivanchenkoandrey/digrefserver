# Generated by Django 3.2.12 on 2022-10-31 09:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth_app', '0057_notification'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='object_id',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Идентификатор связанного объекта'),
        ),
    ]
