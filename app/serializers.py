from app import models
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from rest_framework import serializers

class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'url', 'username', 'email', 'first_name',
                  'last_name',)

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name',)

    def update(self, instance, validated_data):
        instance.email = validated_data.get('email', instance.email)
        instance.first_name = validated_data.get('first_name',
                                                 instance.first_name)
        instance.last_name = validated_data.get('last_name',
                                                instance.last_name)
        instance.save()
        return instance

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
            is_active=False
        )
        user.set_password(validated_data['password'])
        user.save()
        # Generate a unique alphanumeric string to verify the user.
        # This value is persisted to the database and verified during
        # account activation.
        code = get_random_string(length=32)
        verification = models.Verification(verification_code=code,
                                           user=user)
        verification.save()
        return user

class PasswordSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email',)
