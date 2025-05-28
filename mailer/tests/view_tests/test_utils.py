import datetime
from django.test import TestCase, override_settings
from django.core import mail
from django.template.loader import render_to_string
from django.utils import timezone
from unittest import mock

# Import the function to be tested
from mailer.utils import send_templated_email

# Import model factories for easy test data creation
from hire.tests.test_helpers.model_factories import (
    create_user,
    create_driver_profile,
    create_hire_booking,
)

# Import the EmailLog model directly for assertions
from mailer.models import EmailLog


@override_settings(DEFAULT_FROM_EMAIL='default@example.com')
class SendTemplatedEmailTest(TestCase):
    """
    Unit tests for the send_templated_email utility function.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        This runs once for the entire test class.
        """
        cls.user = create_user(username="testuser", email="user@example.com")
        cls.driver_profile = create_driver_profile(email="driver@example.com")
        cls.booking = create_hire_booking(driver_profile=cls.driver_profile)

        # Common email parameters
        cls.recipient_list = ["test@example.com"]
        cls.subject = "Test Email Subject"
        cls.template_name = "emails/test_template.html"
        cls.context = {"name": "Test User", "item": "Test Item"}
        cls.html_content = "<html><body><h1>Hello Test User!</h1><p>Your item: Test Item</p></body></html>"
        cls.text_content = "Hello Test User!\nYour item: Test Item"

    def setUp(self):
        """
        Set up for each test method.
        Clears the outbox and sets up mocks for each test.
        """
        mail.outbox = [] # Clear Django's email outbox before each test

        # Patch render_to_string directly in setUp
        self.mock_render_to_string = mock.patch('mailer.utils.render_to_string').start()
        self.mock_render_to_string.return_value = self.html_content

        # Mock EmailLog.objects.create to prevent actual DB interaction during tests
        self.mock_email_log_create = mock.patch('mailer.utils.EmailLog.objects.create').start()
        self.mock_email_log_create.return_value = mock.Mock(spec=EmailLog)
        self.mock_email_log_create.return_value.status = 'SENT' # Default for mock, overridden by call args

        # Mock the logger to check log messages
        self.mock_logger_error = mock.patch('mailer.utils.logger.error').start()
        self.mock_logger_info = mock.patch('mailer.utils.logger.info').start()
        self.mock_logger_critical = mock.patch('mailer.utils.logger.critical').start()
        self.mock_logger_debug = mock.patch('mailer.utils.logger.debug').start()

        # Ensure all patches are stopped after each test
        self.addCleanup(mock.patch.stopall)


    def test_successful_email_sending(self):
        """
        Test that email is sent successfully and logged with 'SENT' status.
        """
        success = send_templated_email(
            self.recipient_list,
            self.subject,
            self.template_name,
            self.context
        )

        self.assertTrue(success)
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.subject, self.subject)
        self.assertEqual(sent_email.to, self.recipient_list)
        self.assertEqual(sent_email.from_email, 'default@example.com')
        self.assertIn(self.html_content, sent_email.alternatives[0][0])
        self.assertEqual(sent_email.alternatives[0][1], 'text/html')
        self.assertEqual(sent_email.body, self.text_content)

        # Assert EmailLog was created with correct status and data
        self.mock_email_log_create.assert_called_once()
        call_args = self.mock_email_log_create.call_args[1]
        self.assertEqual(call_args['sender'], 'default@example.com')
        self.assertEqual(call_args['recipient'], ", ".join(self.recipient_list))
        self.assertEqual(call_args['subject'], self.subject)
        self.assertEqual(call_args['body'], self.html_content)
        self.assertEqual(call_args['status'], 'SENT')
        self.assertIsNone(call_args['error_message'])
        self.assertIsNone(call_args['user'])
        self.assertIsNone(call_args['driver_profile'])
        self.assertIsNone(call_args['booking'])
        self.mock_logger_info.assert_called_once()
        self.mock_logger_debug.assert_called_once()


    def test_email_sending_failure(self):
        """
        Test that if email sending fails, it's logged with 'FAILED' status and error message.
        """
        # Simulate an error during email sending
        with mock.patch('django.core.mail.EmailMultiAlternatives.send', side_effect=Exception("SMTP Error")):
            success = send_templated_email(
                self.recipient_list,
                self.subject,
                self.template_name,
                self.context
            )

            self.assertFalse(success)
            self.assertEqual(len(mail.outbox), 0) # No email should be in outbox if send fails

            # Assert EmailLog was created with FAILED status and error message
            self.mock_email_log_create.assert_called_once()
            call_args = self.mock_email_log_create.call_args[1]
            self.assertEqual(call_args['status'], 'FAILED')
            self.assertIn("SMTP Error", call_args['error_message'])
            self.mock_logger_error.assert_called_once()
            self.mock_logger_debug.assert_called_once()


    def test_template_rendering_failure(self):
        """
        Test that if template rendering fails, email is not sent and logged with 'FAILED' status.
        """
        # Simulate an error during template rendering
        self.mock_render_to_string.side_effect = Exception("Template Not Found")

        success = send_templated_email(
            self.recipient_list,
            self.subject,
            self.template_name,
            self.context
        )

        self.assertFalse(success)
        self.assertEqual(len(mail.outbox), 0) # No email sent
        self.mock_render_to_string.assert_called_once_with(self.template_name, self.context)

        # Assert EmailLog was created due to rendering failure
        self.mock_email_log_create.assert_called_once()
        call_args = self.mock_email_log_create.call_args[1]
        self.assertEqual(call_args['status'], 'FAILED')
        self.assertIn("Template rendering failed: Template Not Found", call_args['error_message'])
        self.assertIn("Error rendering template:", call_args['body']) # Check body contains error info
        self.mock_logger_error.assert_called_once()
        # No debug log for successful log saving in this path, only critical if log fails
        self.mock_logger_debug.assert_not_called()


    def test_empty_recipient_list(self):
        """
        Test that the function handles an empty recipient list gracefully.
        """
        success = send_templated_email(
            [], # Empty recipient list
            self.subject,
            self.template_name,
            self.context
        )

        self.assertFalse(success)
        self.assertEqual(len(mail.outbox), 0)
        self.mock_render_to_string.assert_not_called() # Should not attempt to render
        self.mock_email_log_create.assert_not_called() # Should not attempt to log an email
        self.mock_logger_error.assert_called_once_with("send_templated_email called with an empty recipient_list.")


    def test_from_email_override(self):
        """
        Test that the from_email argument overrides settings.DEFAULT_FROM_EMAIL.
        """
        custom_from_email = "custom@example.com"
        success = send_templated_email(
            self.recipient_list,
            self.subject,
            self.template_name,
            self.context,
            from_email=custom_from_email
        )

        self.assertTrue(success)
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.from_email, custom_from_email)

        # Assert EmailLog also uses the custom from_email
        self.mock_email_log_create.assert_called_once()
        call_args = self.mock_email_log_create.call_args[1]
        self.assertEqual(call_args['sender'], custom_from_email)


    def test_linking_to_user(self):
        """
        Test that the EmailLog is linked to the provided User instance.
        """
        success = send_templated_email(
            self.recipient_list,
            self.subject,
            self.template_name,
            self.context,
            user=self.user
        )
        self.assertTrue(success)
        self.mock_email_log_create.assert_called_once()
        call_args = self.mock_email_log_create.call_args[1]
        self.assertEqual(call_args['user'], self.user)
        self.assertIsNone(call_args['driver_profile'])
        self.assertIsNone(call_args['booking'])

    def test_linking_to_driver_profile(self):
        """
        Test that the EmailLog is linked to the provided DriverProfile instance.
        """
        success = send_templated_email(
            self.recipient_list,
            self.subject,
            self.template_name,
            self.context,
            driver_profile=self.driver_profile
        )
        self.assertTrue(success)
        self.mock_email_log_create.assert_called_once()
        call_args = self.mock_email_log_create.call_args[1]
        self.assertEqual(call_args['driver_profile'], self.driver_profile)
        self.assertIsNone(call_args['user'])
        self.assertIsNone(call_args['booking'])

    def test_linking_to_booking(self):
        """
        Test that the EmailLog is linked to the provided HireBooking instance.
        """
        success = send_templated_email(
            self.recipient_list,
            self.subject,
            self.template_name,
            self.context,
            booking=self.booking
        )
        self.assertTrue(success)
        self.mock_email_log_create.assert_called_once()
        call_args = self.mock_email_log_create.call_args[1]
        self.assertEqual(call_args['booking'], self.booking)
        self.assertIsNone(call_args['user'])
        self.assertIsNone(call_args['driver_profile'])

    def test_linking_to_all_related_objects(self):
        """
        Test that the EmailLog is linked to all provided related instances.
        """
        success = send_templated_email(
            self.recipient_list,
            self.subject,
            self.template_name,
            self.context,
            user=self.user,
            driver_profile=self.driver_profile,
            booking=self.booking
        )
        self.assertTrue(success)
        self.mock_email_log_create.assert_called_once()
        call_args = self.mock_email_log_create.call_args[1]
        self.assertEqual(call_args['user'], self.user)
        self.assertEqual(call_args['driver_profile'], self.driver_profile)
        self.assertEqual(call_args['booking'], self.booking)

    def test_email_log_critical_error_on_log_failure(self):
        """
        Test that a critical error is logged if EmailLog creation itself fails.
        """
        # Simulate EmailLog.objects.create raising an exception
        self.mock_email_log_create.side_effect = Exception("DB Write Error")

        success = send_templated_email(
            self.recipient_list,
            self.subject,
            self.template_name,
            self.context
        )

        # The function should still return True if the email was sent successfully,
        # even if logging failed.
        self.assertTrue(success)
        self.assertEqual(len(mail.outbox), 1) # Email still sent

        # Assert critical logger was called due to logging failure
        self.mock_logger_critical.assert_called_once()
        self.assertIn("CRITICAL ERROR: Failed to log email", self.mock_logger_critical.call_args[0][0])
        self.assertIn("DB Write Error", self.mock_logger_critical.call_args[0][0])

