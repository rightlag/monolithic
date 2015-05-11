from django.contrib.auth.models import User
from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    """Registration post save event. Creates authentication token for
    newly registered user."""
    if created:
        Token.objects.create(user=instance)

class Keypair(models.Model):
    """Model that contains information regarding AWS key pairs
    (e.g. access keys and secret keys)."""
    name = models.CharField(max_length=255, unique=True)
    access_key = models.CharField(max_length=255)
    secret_key = models.CharField(max_length=255)
    user = models.ManyToManyField(User)

    def __unicode__(self):
        return self.access_key

class Policy(models.Model):
    created = models.DateTimeField()
    policy = models.TextField()
    ignore = models.BooleanField(default=False)
    user = models.ManyToManyField(User)

class Verification(models.Model):
    verification_code = models.CharField(max_length=255)
    user = models.OneToOneField(User)

    def __unicode__(self):
        return self.verification_code
