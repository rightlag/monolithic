from django.contrib.auth.models import User
from django.test import TestCase

class RegisterTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='TestUser',
                                        email='example@domain.com')

    def has_auth_token(self):
        """Assert user has `auth_token` attribute after account
        creation."""
        self.assertEqual(hasattr(self.user, 'auth_token'), True)
