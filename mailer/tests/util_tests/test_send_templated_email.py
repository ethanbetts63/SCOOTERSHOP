from django.test import TestCase
from unittest.mock import patch, MagicMock
from django.conf import settings
from mailer.utils.send_templated_email import send_templated_email
from mailer.models.EmailLog_model import EmailLog
from mailer.tests.test_helpers.model_factories import UserFactory, ServiceProfileFactory, SalesProfileFactory, ServiceBookingFactory, SalesBookingFactory


class SendTemplatedEmailTest(TestCase):

    def setUp(self):
        self.user = UserFactory()
        self.service_profile = ServiceProfileFactory(user=self.user)
        self.sales_profile = SalesProfileFactory(user=self.user)
        self.service_booking = ServiceBookingFactory(service_profile=self.service_profile)
        self.sales_booking = SalesBookingFactory(sales_profile=self.sales_profile)

        self.recipient_list = ["test@example.com"]
        self.subject = "Test Subject"
        self.template_name = "test_template.html"
        self.context = {"name": "Test User"}

        # Ensure a default from email is set for tests
        settings.DEFAULT_FROM_EMAIL = "default@example.com"

    @patch('mailer.utils.send_templated_email.EmailMultiAlternatives')
    @patch('mailer.utils.send_templated_email.render_to_string')
    def test_send_templated_email_success(self, mock_render_to_string, mock_email_multi_alternatives):
        mock_render_to_string.return_value = "<html><body><h1>Hello</h1><p>Test</p></body></html>"
        mock_email_instance = MagicMock()
        mock_email_multi_alternatives.return_value = mock_email_instance

        success = send_templated_email(
            self.recipient_list, self.subject, self.template_name, self.context,
            booking=self.service_booking, profile=self.service_profile
        )

        self.assertTrue(success)
        mock_render_to_string.assert_called_once_with(self.template_name, {
            'name': 'Test User',
            'booking': self.service_booking,
            'profile': self.service_profile,
            'user': self.user
        })
        mock_email_multi_alternatives.assert_called_once_with(
            self.subject, "Hello\nTest", settings.DEFAULT_FROM_EMAIL, self.recipient_list
        )
        mock_email_instance.attach_alternative.assert_called_once_with(
            "<html><body><h1>Hello</h1><p>Test</p></body></html>", "text/html"
        )
        mock_email_instance.send.assert_called_once()

        email_log = EmailLog.objects.latest('timestamp')
        self.assertEqual(email_log.status, 'SENT')
        self.assertEqual(email_log.subject, self.subject)
        self.assertEqual(email_log.recipient, ", ".join(self.recipient_list))
        self.assertEqual(email_log.service_booking, self.service_booking)
        self.assertEqual(email_log.service_profile, self.service_profile)

    @patch('mailer.utils.send_templated_email.EmailMultiAlternatives')
    @patch('mailer.utils.send_templated_email.render_to_string')
    def test_send_templated_email_failure_rendering(self, mock_render_to_string, mock_email_multi_alternatives):
        mock_render_to_string.side_effect = Exception("Template error")

        success = send_templated_email(
            self.recipient_list, self.subject, self.template_name, self.context,
            booking=self.sales_booking, profile=self.sales_profile
        )

        self.assertFalse(success)
        mock_email_multi_alternatives.assert_not_called()
        email_log = EmailLog.objects.latest('timestamp')
        self.assertEqual(email_log.status, 'FAILED')
        self.assertIn("Template rendering failed", email_log.error_message)
        self.assertEqual(email_log.sales_booking, self.sales_booking)
        self.assertEqual(email_log.sales_profile, self.sales_profile)

    @patch('mailer.utils.send_templated_email.EmailMultiAlternatives')
    @patch('mailer.utils.send_templated_email.render_to_string')
    def test_send_templated_email_failure_sending(self, mock_render_to_string, mock_email_multi_alternatives):
        mock_render_to_string.return_value = "<html><body>Test</body></html>"
        mock_email_instance = MagicMock()
        mock_email_multi_alternatives.return_value = mock_email_instance
        mock_email_instance.send.side_effect = Exception("SMTP error")

        success = send_templated_email(
            self.recipient_list, self.subject, self.template_name, self.context,
            booking=self.service_booking, profile=self.service_profile
        )

        self.assertFalse(success)
        email_log = EmailLog.objects.latest('timestamp')
        self.assertEqual(email_log.status, 'FAILED')
        self.assertIn("SMTP error", email_log.error_message)

    def test_send_templated_email_no_recipient(self):
        success = send_templated_email(
            [], self.subject, self.template_name, self.context,
            booking=self.service_booking, profile=self.service_profile
        )
        self.assertFalse(success)
        self.assertEqual(EmailLog.objects.count(), 0) # No log should be created if no recipient

    @patch('mailer.utils.send_templated_email.EmailMultiAlternatives')
    @patch('mailer.utils.send_templated_email.render_to_string')
    def test_send_templated_email_with_sales_booking_and_profile(self, mock_render_to_string, mock_email_multi_alternatives):
        mock_render_to_string.return_value = "<html><body>Sales Test</body></html>"
        mock_email_instance = MagicMock()
        mock_email_multi_alternatives.return_value = mock_email_instance

        success = send_templated_email(
            self.recipient_list, self.subject, self.template_name, self.context,
            booking=self.sales_booking, profile=self.sales_profile
        )

        self.assertTrue(success)
        email_log = EmailLog.objects.latest('timestamp')
        self.assertEqual(email_log.status, 'SENT')
        self.assertEqual(email_log.sales_booking, self.sales_booking)
        self.assertEqual(email_log.sales_profile, self.sales_profile)
        self.assertIsNone(email_log.service_booking)
        self.assertIsNone(email_log.service_profile)

    @patch('mailer.utils.send_templated_email.EmailMultiAlternatives')
    @patch('mailer.utils.send_templated_email.render_to_string')
    def test_send_templated_email_html_to_text_conversion(self, mock_render_to_string, mock_email_multi_alternatives):
        html_content = "<html><body><h1>Title</h1><p>Paragraph 1</p><br><div>Div content</div><ul><li>Item 1</li><li>Item 2</li></ul></body></html>"
        mock_render_to_string.return_value = html_content
        mock_email_instance = MagicMock()
        mock_email_multi_alternatives.return_value = mock_email_instance

        send_templated_email(
            self.recipient_list, self.subject, self.template_name, self.context,
            booking=self.service_booking, profile=self.service_profile
        )

        expected_text_content = "Title\nParagraph 1\n\n\nDiv content\nItem 1\nItem 2"
        args, kwargs = mock_email_multi_alternatives.call_args
        self.assertEqual(args[1].strip(), expected_text_content.strip())