from django.test import TestCase
from unittest.mock import patch, MagicMock
from django.conf import settings
from mailer.utils.send_templated_email import send_templated_email
from mailer.models import EmailLog
from mailer.tests.test_helpers.model_factories import EmailLogFactory
from users.tests.test_helpers.model_factories import UserFactory
from service.tests.test_helpers.model_factories import ServiceProfileFactory, ServiceBookingFactory, ServiceTypeFactory
from inventory.tests.test_helpers.model_factories import SalesProfileFactory, SalesBookingFactory

class SendTemplatedEmailTest(TestCase):

    def setUp(self):
        self.user = UserFactory()
        self.service_type = ServiceTypeFactory()
        self.service_profile = ServiceProfileFactory(user=self.user)
        self.sales_profile = SalesProfileFactory(user=self.user)
        self.service_booking = ServiceBookingFactory(service_profile=self.service_profile, service_type=self.service_type)
        self.sales_booking = SalesBookingFactory(sales_profile=self.sales_profile)

        self.recipient_list = ["test@example.com"]
        self.subject = "Test Subject"
        self.template_name = "test_template.html"
        self.context = {"name": "Test User"}

        settings.DEFAULT_FROM_EMAIL = "default@example.com"

    @patch('mailer.utils.send_templated_email.EmailMultiAlternatives')
    def test_send_templated_email_success_creates_log(self, mock_email_multi_alternatives):
        # Arrange
        mock_email_instance = MagicMock()
        mock_email_multi_alternatives.return_value = mock_email_instance

        # Act
        success = send_templated_email(
            self.recipient_list, self.subject, self.template_name, self.context,
            booking=self.service_booking, profile=self.service_profile
        )

        # Assert
        self.assertTrue(success)
        self.assertEqual(EmailLog.objects.count(), 1)
        email_log = EmailLog.objects.first()
        self.assertEqual(email_log.status, 'SENT')
        self.assertEqual(email_log.subject, self.subject)
        self.assertEqual(email_log.recipient, ", ".join(self.recipient_list))
        self.assertEqual(email_log.service_booking, self.service_booking)
        self.assertEqual(email_log.service_profile, self.service_profile)
        mock_email_instance.send.assert_called_once()

    @patch('mailer.utils.send_templated_email.render_to_string', side_effect=Exception("Template Error"))
    def test_send_templated_email_template_error_creates_log(self, mock_render_to_string):
        # Act
        success = send_templated_email(
            self.recipient_list, self.subject, self.template_name, self.context,
            booking=self.sales_booking, profile=self.sales_profile
        )

        # Assert
        self.assertFalse(success)
        self.assertEqual(EmailLog.objects.count(), 1)
        email_log = EmailLog.objects.first()
        self.assertEqual(email_log.status, 'FAILED')
        self.assertIn('Template rendering failed', email_log.error_message)
        self.assertEqual(email_log.sales_booking, self.sales_booking)
        self.assertEqual(email_log.sales_profile, self.sales_profile)

    @patch('mailer.utils.send_templated_email.EmailMultiAlternatives', side_effect=Exception("SMTP Error"))
    def test_send_templated_email_send_error_creates_log(self, mock_email_multi_alternatives):
        # Act
        success = send_templated_email(
            self.recipient_list, self.subject, self.template_name, self.context,
            booking=self.service_booking, profile=self.service_profile
        )

        # Assert
        self.assertFalse(success)
        self.assertEqual(EmailLog.objects.count(), 1)
        email_log = EmailLog.objects.first()
        self.assertEqual(email_log.status, 'FAILED')
        self.assertIn('SMTP Error', email_log.error_message)
