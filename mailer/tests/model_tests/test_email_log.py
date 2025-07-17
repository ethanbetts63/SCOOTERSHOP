from django.test import TestCase
from mailer.models.EmailLog_model import EmailLog
from mailer.tests.test_helpers.model_factories import EmailLogFactory
from users.tests.test_helpers.model_factories import UserFactory
from service.tests.test_helpers.model_factories import (
    ServiceProfileFactory,
    ServiceBookingFactory,
)
from inventory.tests.test_helpers.model_factories import (
    SalesProfileFactory,
    SalesBookingFactory,
)


class EmailLogModelTest(TestCase):
    def test_email_log_creation(self):
        email_log = EmailLogFactory()
        self.assertIsInstance(email_log, EmailLog)
        self.assertIsNotNone(email_log.pk)
        self.assertIn(email_log.status, ["SENT", "FAILED", "PENDING"])

    def test_email_log_str_representation(self):
        email_log = EmailLogFactory(
            subject="Test Subject", recipient="test@example.com", status="SENT"
        )
        self.assertEqual(
            str(email_log), "Email to test@example.com - Subject: 'Test Subject' (SENT)"
        )

    def test_email_log_with_user(self):
        user = UserFactory()
        email_log = EmailLogFactory(user=user)
        self.assertEqual(email_log.user, user)

    def test_email_log_with_service_profile(self):
        service_profile = ServiceProfileFactory()
        email_log = EmailLogFactory(service_profile=service_profile)
        self.assertEqual(email_log.service_profile, service_profile)

    def test_email_log_with_sales_profile(self):
        sales_profile = SalesProfileFactory()
        email_log = EmailLogFactory(sales_profile=sales_profile)
        self.assertEqual(email_log.sales_profile, sales_profile)

    def test_email_log_with_service_booking(self):
        service_booking = ServiceBookingFactory()
        email_log = EmailLogFactory(service_booking=service_booking)
        self.assertEqual(email_log.service_booking, service_booking)

    def test_email_log_with_sales_booking(self):
        sales_booking = SalesBookingFactory()
        email_log = EmailLogFactory(sales_booking=sales_booking)
        self.assertEqual(email_log.sales_booking, sales_booking)

    def test_email_log_status_choices(self):
        for status_choice, _ in EmailLog.STATUS_CHOICES:
            email_log = EmailLogFactory(status=status_choice)
            self.assertEqual(email_log.status, status_choice)

    def test_email_log_error_message(self):
        email_log = EmailLogFactory(
            status="FAILED", error_message="SMTP Connection Error"
        )
        self.assertEqual(email_log.status, "FAILED")
        self.assertEqual(email_log.error_message, "SMTP Connection Error")
