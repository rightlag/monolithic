import boto
import boto.ec2
import boto.exception
import boto.s3
import datetime

from app import core
from app import models
from app import serializers
from django.contrib.auth.models import User
from django.core import mail
from django.test import Client
from django.test import TestCase
from django.utils.crypto import get_random_string
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from rest_framework.test import APITestCase

class RegisterTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User(username='TestUser', email='example@domain.com')
        self.user.is_active = False
        self.user.set_password('password')
        self.user.save()
        self.code = get_random_string(length=32)
        verification = models.Verification(verification_code=self.code,
                                           user=self.user)
        verification.save()

    def test_user_has_auth_token(self):
        """Assert user has `auth_token` attribute after account
        creation."""
        self.assertIsNotNone(self.user.auth_token.key)

    def test_user_has_verification_token(self):
        """Assert user has `verification` attribute."""
        self.assertIsNotNone(self.user.verification)

    def test_registration_is_successful(self):
        response = self.client.post('/api/v1/users/register/', {
            'username': 'test_user',
            'email': 'rightlag@gmail.com',
            'password': 'test_password',
        })
        self.assertEqual(response.status_code, 201)

    def test_user_account_is_verified(self):
        """Assert that user verification returns a HTTP 200 OK
        response."""
        response = self.client.get('/api/v1/auth/verify/{}/'
                                   .format(self.code))
        self.assertEqual(response.status_code, 200)

class ProfileTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User(username='TestUser', email='example@domain.com')
        self.user.set_password('password')
        self.user.save()

    def test_user_has_updated_profile(self):
        """Assert user object is updated accordingly."""
        data = {
            'first_name': 'John',
            'last_name': 'Smith',
            'email': 'JohnSmith@domain.com',
        }
        serializer = serializers.ProfileSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            serializer.update(self.user, data)
        self.assertEqual(self.user.first_name, 'John')
        self.assertEqual(self.user.last_name, 'Smith')
        self.assertEqual(self.user.email, 'JohnSmith@domain.com')

    def test_user_has_updated_password(self):
        response = self.client.post('/api/v1/users/reset/', {
            'username': 'TestUser',
        })
        self.assertEqual(response.status_code, 200)

    def test_user_has_valid_access_and_secret_keys(self):
        """Assert that the call to `get_all_regions` method returns a
        401 status code, since the AWS access key and secret key are
        invalid."""
        aws_access_key_id = get_random_string(length=32)
        aws_secret_access_key = get_random_string(length=32)
        conn = boto.connect_ec2(aws_access_key_id=aws_access_key_id,
                                aws_secret_access_key=aws_secret_access_key)
        try:
            conn.get_all_regions()
        except boto.exception.EC2ResponseError, e:
            self.assertEqual(e.status, 401)

class EmailTest(TestCase):
    def test_send_email(self):
        """Assert that mail is sent via SES service."""
        mail.send_mail('Subject here',
                       'Here is the message.',
                       'from@example.com',
                       ['to@example.com'],
                       fail_silently=False)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Subject here')

class PolicyTestCase(TestCase):
    def setUp(self):
        self.conn = boto.s3.connect_to_region(core.DEFAULT_AWS_REGION)
        try:
            self.bucket = self.conn.get_all_buckets()[0]
        except IndexError, e:
            raise e

    def test_policy_list_is_not_none(self):
        """Assert that the policy list is not zero after creating a new
        policy."""
        data = {
            'region': core.DEFAULT_AWS_REGION,
            'bucket': self.bucket.name,
        }
        serializer = serializers.PolicySerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            policy = serializer.create(serializer.data)
        self.assertEqual(len(models.Policy.objects.all()), 1)
