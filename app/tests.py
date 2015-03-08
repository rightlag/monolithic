from app import models
from app import serializers
from django.contrib.auth.models import User
from django.test import Client
from django.test import TestCase
from django.utils.crypto import get_random_string

class RegisterTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User(username='TestUser', email='example@domain.com')
        self.user.set_password('password')
        self.user.save()
        code = get_random_string(length=32)
        verification = models.Verification(verification_code=code,
                                           user=self.user)
        verification.save()

    def test_user_has_auth_token(self):
        """Assert user has `auth_token` attribute after account
        creation."""
        self.assertIsNotNone(self.user.auth_token.key)

    def test_user_has_verification_token(self):
        """Assert user has `verification` attribute."""
        self.assertIsNotNone(self.user.verification)

    def test_registration_email_verification(self):
        response = self.client.post('/api/v1/users/register/', {
            'username': 'test_user',
            'email': 'rightlag@gmail.com',
            'password': 'test_password',
        })
        self.assertEqual(response.status_code, 201)

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
        pass

    def test_reset_email_verification(self):
        response = self.client.post('/api/v1/users/reset/', {
            'username': 'TestUser',
        })
        self.assertEqual(response.status_code, 200)
