import smtplib

from django.contrib.auth.models import User
from django.core.mail import send_mail
from rest_framework import serializers

class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'url', 'username',)

class RegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'username', 'password',)

    def create(self, validated_data):
        """Create user via credentials provided. `set_password` method
        called after instantiation to ensure password hashing."""
        user = User(
            email=validated_data['email'],
            username=validated_data['username'],
            is_active=False,
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

class PasswordSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email',)
