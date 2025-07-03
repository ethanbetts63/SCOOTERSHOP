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

    @patch('dashboard.views.index.render')
    def test_dashboard_index_view_staff_access(self, mock_render):
        mock_render.return_value = HttpResponse()
        self.client.login(username=self.staff_user.username, password='testpassword')
        response = self.client.get(reverse('dashboard:dashboard_index'))
        self.assertEqual(response.status_code, 200)
        mock_render.assert_called_once_with(ANY, 'dashboard/dashboard_index.html', ANY)

    @patch('dashboard.views.index.render')
    def test_dashboard_index_view_non_staff_access(self, mock_render):
        mock_render.return_value = HttpResponse()
        self.client.login(username=self.non_staff_user.username, password='testpassword')
        response = self.client.get(reverse('dashboard:dashboard_index'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
        mock_render.assert_not_called()
