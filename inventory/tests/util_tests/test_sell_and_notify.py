from django.test import TestCase
from django.core import mail
from inventory.utils.sell_and_notify import sell_and_notify
from inventory.tests.test_helpers.model_factories import MotorcycleFactory, SalesBookingFactory, SalesProfileFactory
from users.tests.test_helpers.model_factories import UserFactory


class SellAndNotifyTests(TestCase):

    def setUp(self):
        self.motorcycle = MotorcycleFactory(status='available')
        self.user1 = UserFactory()
        self.sales_profile1 = SalesProfileFactory(user=self.user1)
        self.booking1 = SalesBookingFactory(
            motorcycle=self.motorcycle,
            sales_profile=self.sales_profile1,
            payment_status='unpaid'
        )

        self.user2 = UserFactory()
        self.sales_profile2 = SalesProfileFactory(user=self.user2)
        self.booking2 = SalesBookingFactory(
            motorcycle=self.motorcycle,
            sales_profile=self.sales_profile2,
            payment_status='deposit_paid',  # This one should not be notified
            booking_status='pending_confirmation'
        )

        self.user3 = UserFactory()
        self.sales_profile3 = SalesProfileFactory(user=self.user3)
        self.booking3 = SalesBookingFactory(
            motorcycle=self.motorcycle,
            sales_profile=self.sales_profile3,
            payment_status='unpaid'
        )

    def test_motorcycle_status_updated_to_sold(self):
        sell_and_notify(self.motorcycle)
        self.motorcycle.refresh_from_db()
        self.assertEqual(self.motorcycle.status, 'sold')

    def test_emails_sent_only_to_non_deposit_bookings(self):
        sell_and_notify(self.motorcycle)
        self.assertEqual(len(mail.outbox), 2)

        recipient_emails = sorted([email.to[0] for email in mail.outbox])
        expected_emails = sorted([self.user1.email, self.user3.email])
        self.assertEqual(recipient_emails, expected_emails)

    def test_email_content(self):
        sell_and_notify(self.motorcycle)
        self.assertEqual(len(mail.outbox), 2)

        email = mail.outbox[0]
        self.assertEqual(email.subject, f'Update on your interest in the {self.motorcycle.title}')
        self.assertIn(self.motorcycle.title, email.body)
        self.assertIn('has now been sold and is no longer available', email.body)

    def test_non_deposit_booking_status_updated_to_cancelled(self):
        sell_and_notify(self.motorcycle)
        self.booking1.refresh_from_db()
        self.booking3.refresh_from_db()
        self.booking2.refresh_from_db()

        self.assertEqual(self.booking1.booking_status, 'cancelled')
        self.assertEqual(self.booking3.booking_status, 'cancelled')
        self.assertNotEqual(self.booking2.booking_status, 'cancelled') # Ensure deposit booking is not cancelled
