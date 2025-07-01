import datetime
from django.test import TestCase
from django.utils import timezone

                                                    
from hire.tests.test_helpers.model_factories import (
    create_user,
    create_driver_profile,
    create_hire_booking,
    create_email_log,                                   
)

                                                   
from mailer.models import EmailLog


class EmailLogModelTest(TestCase):
    """
    Unit tests for the EmailLog model.
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

    def test_email_log_creation_basic(self):
        """
        Test that an EmailLog instance can be created with basic required fields.
        """
        email_log = create_email_log(
            sender="admin@example.com",
            recipient="customer@example.com",
            subject="Your Order Confirmation",
            body="<html><body><h1>Order Confirmed!</h1></body></html>",
            status='SENT'
        )
        self.assertIsInstance(email_log, EmailLog)
        self.assertEqual(email_log.sender, "admin@example.com")
        self.assertEqual(email_log.recipient, "customer@example.com")
        self.assertEqual(email_log.subject, "Your Order Confirmation")
        self.assertEqual(email_log.body, "<html><body><h1>Order Confirmed!</h1></body></html>")
        self.assertEqual(email_log.status, 'SENT')
        self.assertIsNotNone(email_log.timestamp)
        self.assertIsNone(email_log.error_message)
        self.assertIsNone(email_log.user)
        self.assertIsNone(email_log.driver_profile)
        self.assertIsNone(email_log.booking)

    def test_email_log_creation_with_default_status(self):
        """
        Test that an EmailLog instance is created with 'PENDING' status by default.
        """
                                                                            
        email_log = create_email_log(
            sender="admin@example.com",
            recipient="customer@example.com",
            subject="Default Status Test",
            body="Test body.",
                                                        
        )
        self.assertEqual(email_log.status, 'PENDING')

    def test_email_log_with_error_message(self):
        """
        Test that an EmailLog instance can store an error message.
        """
        error_msg = "SMTP connection failed."
        email_log = create_email_log(
            sender="admin@example.com",
            recipient="customer@example.com",
            subject="Failed Email",
            body="Failed to send.",
            status='FAILED',
            error_message=error_msg
        )
        self.assertEqual(email_log.status, 'FAILED')
        self.assertEqual(email_log.error_message, error_msg)

    def test_email_log_with_user_fk(self):
        """
        Test that an EmailLog instance can be linked to a User.
        """
        email_log = create_email_log(
            sender="admin@example.com",
            recipient=self.user.email,
            subject="User Email",
            body="Hello User!",
            user=self.user
        )
        self.assertEqual(email_log.user, self.user)
        self.assertIsNone(email_log.driver_profile)
        self.assertIsNone(email_log.booking)
        self.assertEqual(self.user.sent_emails.count(), 1)
        self.assertEqual(self.user.sent_emails.first(), email_log)

    def test_email_log_with_driver_profile_fk(self):
        """
        Test that an EmailLog instance can be linked to a DriverProfile.
        """
        email_log = create_email_log(
            sender="admin@example.com",
            recipient=self.driver_profile.email,
            subject="Driver Profile Email",
            body="Hello Driver!",
            driver_profile=self.driver_profile
        )
        self.assertEqual(email_log.driver_profile, self.driver_profile)
        self.assertIsNone(email_log.user)
        self.assertIsNone(email_log.booking)
        self.assertEqual(self.driver_profile.sent_emails.count(), 1)
        self.assertEqual(self.driver_profile.sent_emails.first(), email_log)

    def test_email_log_with_booking_fk(self):
        """
        Test that an EmailLog instance can be linked to a HireBooking.
        """
        email_log = create_email_log(
            sender="admin@example.com",
            recipient="booking_customer@example.com",
            subject="Booking Confirmation",
            body="Booking details...",
            booking=self.booking
        )
        self.assertEqual(email_log.booking, self.booking)
        self.assertIsNone(email_log.user)
        self.assertIsNone(email_log.driver_profile)
        self.assertEqual(self.booking.related_emails.count(), 1)
        self.assertEqual(self.booking.related_emails.first(), email_log)

    def test_email_log_str_method(self):
        """
        Test the __str__ method of the EmailLog model.
        """
        email_log = create_email_log(
            sender="admin@example.com",
            recipient="test@example.com",
            subject="Test Subject for Str",
            status='SENT'
        )
        expected_str = "Email to test@example.com - Subject: 'Test Subject for Str' (SENT)"
        self.assertEqual(str(email_log), expected_str)

        email_log_failed = create_email_log(
            sender="admin@example.com",
            recipient="fail@example.com",
            subject="Failed Email Test",
            status='FAILED'
        )
        expected_str_failed = "Email to fail@example.com - Subject: 'Failed Email Test' (FAILED)"
        self.assertEqual(str(email_log_failed), expected_str_failed)

    def test_email_log_timestamp_auto_now_add(self):
        """
        Test that the timestamp is automatically set upon creation when not provided.
        """
                                                                   
        before_creation = timezone.now()
        email_log = create_email_log(
            sender="t@t.com",
            recipient="r@r.com",
            subject="Timestamp Test",
            body="Body",
            timestamp=None                                            
        )
        after_creation = timezone.now()

        self.assertIsNotNone(email_log.timestamp)
                                                               
        self.assertTrue(before_creation <= email_log.timestamp <= after_creation)

    def test_email_log_ordering(self):
        """
        Test that EmailLog instances are ordered by timestamp in descending order.
        """
                                               
        log1 = create_email_log(
            sender="s1@e.com", recipient="r1@e.com", subject="Log 1",
            timestamp=timezone.now() - datetime.timedelta(minutes=10)
        )
        log2 = create_email_log(
            sender="s2@e.com", recipient="r2@e.com", subject="Log 2",
            timestamp=timezone.now() - datetime.timedelta(minutes=5)
        )
        log3 = create_email_log(
            sender="s3@e.com", recipient="r3@e.com", subject="Log 3",
            timestamp=timezone.now()
        )

                                                 
        all_logs = EmailLog.objects.all()
        self.assertEqual(list(all_logs), [log3, log2, log1])
