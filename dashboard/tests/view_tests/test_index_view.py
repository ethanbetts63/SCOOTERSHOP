from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, ANY
from django.http import HttpResponse
from dashboard.tests.test_helpers.model_factories import StaffUserFactory, UserFactory

class DashboardIndexViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.staff_user = StaffUserFactory()
        self.non_staff_user = UserFactory()

