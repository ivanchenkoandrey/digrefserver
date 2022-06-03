from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

User = get_user_model()


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    tg_id = models.CharField(max_length=20)


@receiver(post_save, sender=User)
def create_auth_token(instance, created, **kwargs):
    if created:
        Token.objects.create(user=instance)
