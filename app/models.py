from django.contrib.auth.models import User
from django.db import models

# Create your models here.

class Keypair(models.Model):
    access_key = models.CharField(max_length=255)
    secret_key = models.CharField(max_length=255)
    user = models.ManyToManyField(User)

    def __unicode__(self):
        return self.access_key

class Policy(models.Model):
    name = models.CharField(max_length=255)
    created = models.DateTimeField()
    policy = models.TextField()
    user = models.ManyToManyField(User)

    def __unicode__(self):
        return self.name
