# Generated by Django 3.2.12 on 2022-09-13 17:19

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('auth_app', '0034_alter_objecttag_tagged_object'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comment',
            name='previous_comment',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='next_comment', to='auth_app.comment', verbose_name='Ссылка на предыдущий комментарий'),
        ),
    ]
