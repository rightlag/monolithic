from app import serializers
from django.contrib.auth.models import User
from django.test import TestCase

class RegisterTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='TestUser',
                                        email='example@domain.com')

    def test_user_has_auth_token(self):
        """Assert user has `auth_token` attribute after account
        creation."""
        self.assertEqual(hasattr(self.user, 'auth_token'), True)

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
