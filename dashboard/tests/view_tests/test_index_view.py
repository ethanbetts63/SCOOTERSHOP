from django.test import TestCase, Client
from dashboard.tests.test_helpers.model_factories import StaffUserFactory, UserFactory

class DashboardIndexViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.staff_user = StaffUserFactory()
        self.non_staff_user = UserFactory()

