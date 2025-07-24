from django.test import TestCase
from inventory.tests.test_helpers.model_factories import SalesBookingFactory
from service.tests.test_helpers.model_factories import ServiceBookingFactory
from core.tests.test_helpers.model_factories import EnquiryFactory
from refunds.tests.test_helpers.model_factories import RefundRequestFactory, RefundSettingsFactory
from dashboard.models import Notification


class SignalTest(TestCase):
    def test_create_sales_booking_notification(self):
        SalesBookingFactory()
        self.assertEqual(Notification.objects.count(), 1)
        notification = Notification.objects.first()
        self.assertIn("New sales booking from", notification.message)

    def test_create_service_booking_notification(self):
        ServiceBookingFactory()
        self.assertEqual(Notification.objects.count(), 1)
        notification = Notification.objects.first()
        self.assertIn("New service booking for", notification.message)

    def test_create_enquiry_notification(self):
        EnquiryFactory()
        self.assertEqual(Notification.objects.count(), 1)
        notification = Notification.objects.first()
        self.assertIn("New enquiry from", notification.message)

    def test_create_refund_notification(self):
        RefundRequestFactory()
        self.assertEqual(Notification.objects.count(), 1)
        notification = Notification.objects.first()
        self.assertIn("New refund request for", notification.message)

    def test_create_refund_settings_notification(self):
        RefundSettingsFactory()
        self.assertEqual(Notification.objects.count(), 1)
        notification = Notification.objects.first()
        self.assertEqual(
            notification.message,
            "Refund settings have been created. Please review the refund policy text.",
        )

    def test_update_refund_settings_notification(self):
        settings = RefundSettingsFactory()
        Notification.objects.all().delete()  # Clear notifications created by initial save
        settings.save()
        self.assertEqual(Notification.objects.count(), 1)
        notification = Notification.objects.first()
        self.assertEqual(
            notification.message,
            "Refund settings have been updated. Please review the refund policy text to ensure it reflects the changes.",
        )
