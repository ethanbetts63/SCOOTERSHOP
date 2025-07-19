from django.test import TestCase
from django.contrib.auth import get_user_model

from users.tests.test_helpers.model_factories import UserFactory, StaffUserFactory, SuperUserFactory

User = get_user_model()


class UserModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.staff_user = StaffUserFactory()
        cls.superuser = SuperUserFactory()

    def test_user_creation(self):
        self.assertIsInstance(self.user, User)
        self.assertIsNotNone(self.user.pk)
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)

    def test_staff_user_creation(self):
        self.assertIsInstance(self.staff_user, User)
        self.assertTrue(self.staff_user.is_staff)
        self.assertFalse(self.staff_user.is_superuser)

    def test_superuser_creation(self):
        self.assertIsInstance(self.superuser, User)
        self.assertTrue(self.superuser.is_staff)
        self.assertTrue(self.superuser.is_superuser)

    def test_str_method(self):
        self.assertEqual(
            str(self.user),
            f"{self.user.username} ({self.user.get_full_name() or self.user.email})",
        )

    def test_user_fields(self):
        self.assertIsInstance(self.user.username, str)
        self.assertIsInstance(self.user.email, str)
        self.assertIsInstance(self.user.first_name, str)
        self.assertIsInstance(self.user.last_name, str)
        self.assertTrue(self.user.is_active)
