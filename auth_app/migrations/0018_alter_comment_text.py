# Generated by Django 3.2.12 on 2022-09-06 23:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth_app', '0017_auto_20220907_0143'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comment',
            name='text',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='Текст'),
        ),
    ]