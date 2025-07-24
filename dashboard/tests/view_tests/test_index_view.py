from django.test import TestCase, Client
from django.urls import reverse
from users.tests.test_helpers.model_factories import UserFactory
from inventory.tests.test_helpers.model_factories import SalesBookingFactory
from dashboard.models import Notification


class DashboardIndexViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = UserFactory(is_staff=True)
        self.client.force_login(self.user)
        self.sales_booking = SalesBookingFactory()

    def test_dashboard_index_view(self):
        response = self.client.get(reverse("dashboard:dashboard_index"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/dashboard_index.html")
        self.assertIn("page_title", response.context)
        self.assertEqual(response.context["page_title"], "Admin Dashboard")
        self.assertIn("notifications", response.context)
        self.assertEqual(len(response.context["notifications"]), 1)


class ClearNotificationsViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = UserFactory(is_staff=True)
        self.client.force_login(self.user)
        self.sales_booking = SalesBookingFactory()

    def test_clear_notifications_view(self):
        self.assertEqual(Notification.objects.filter(is_cleared=False).count(), 1)
        response = self.client.post(reverse("dashboard:clear_notifications"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Notification.objects.filter(is_cleared=False).count(), 0)
