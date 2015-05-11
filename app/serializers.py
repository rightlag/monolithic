import boto.exception
import boto.s3
import json

from app import helpers
from app import models
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.crypto import get_random_string
from rest_framework import serializers

class ComplexEncoder(json.JSONEncoder):
    """Class used to serialize objects returned from AWS API."""
    def default(self, obj):
        if hasattr(obj, '__dict__'):
            data = {}
            for key, val in obj.__dict__.iteritems():
                if hasattr(val, '__dict__'):
                    # To avoid circular references
                    continue
                elif hasattr(val, 'isoformat'):
                    # For date/datetime objects
                    data[key] = val.isoformat()
                elif isinstance(val, list) or isinstance(val, tuple):
                    elements = []
                    for element in val:
                        if hasattr(element, '__name__'):
                            # If element is a class reference
                            elements.append(element.__name__)
                        else:
                            elements.append(element)
                    data[key] = elements
                else:
                    data[key] = val
            return data
        else:
            return json.JSONEncoder.default(self, obj)

class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'url', 'username', 'email', 'first_name',
                  'last_name',)

class KeypairSerializer(serializers.ModelSerializer):
    """AWS Access Key and Secret Key serializer."""
    class Meta:
        model = models.Keypair
        fields = ('id', 'name', 'access_key', 'secret_key',)

class ProfileSerializer(serializers.ModelSerializer):
    keypair_set = KeypairSerializer(many=True, read_only=True)
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'keypair_set',)

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
        fields = ('username',)

class PolicyListSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Policy
        fields = ('id', 'created', 'ignore', 'policy',)

class PolicySerializer(serializers.ModelSerializer):
    region = serializers.CharField()
    bucket = serializers.CharField()
    class Meta:
        model = models.Policy
        fields = ('region', 'bucket', 'ignore',)

    def create(self, validated_data):
        conn = boto.s3.connect_to_region(validated_data.get('region'))
        try:
            # This is redundant, since it is handled in the view, but
            # the `QueryDict` object has proven to be immutable.
            # Therefore, this try/except block will suffice for now.
            bucket = conn.get_bucket(validated_data.get('bucket'))
            policy = bucket.get_policy()
        except boto.exception.S3ResponseError, e:
            # Will never be handled since it is handled in the view.
            raise e
        data = {
            'created': timezone.now(),
            'policy': bucket.get_policy(),
        }
        policy = models.Policy(**data)
        policy.save()
        return policy

    def update(self, instance, validated_data):
        instance.created = validated_data.get('created', instance.created)
        instance.policy = validated_data.get('policy', instance.policy)
        instance.ignore = validated_data.get('ignore', instance.ignore)
        instance.save()
        return instance
