from django.test import TestCase
from django.core import mail
from inventory.utils.sell_and_notify import sell_and_notify
from ..test_helpers.model_factories import MotorcycleFactory, SalesBookingFactory, SalesProfileFactory, UserFactory


class SellAndNotifyTests(TestCase):

    def setUp(self):
        self.motorcycle = MotorcycleFactory(status='available')
        self.user1 = UserFactory()
        self.sales_profile1 = SalesProfileFactory(user=self.user1)
        self.booking1 = SalesBookingFactory(
            motorcycle=self.motorcycle,
            sales_profile=self.sales_profile1,
            deposit_made=False
        )

        self.user2 = UserFactory()
        self.sales_profile2 = SalesProfileFactory(user=self.user2)
        self.booking2 = SalesBookingFactory(
            motorcycle=self.motorcycle,
            sales_profile=self.sales_profile2,
            deposit_made=True  # This one should not be notified
        )

        self.user3 = UserFactory()
        self.sales_profile3 = SalesProfileFactory(user=self.user3)
        self.booking3 = SalesBookingFactory(
            motorcycle=self.motorcycle,
            sales_profile=self.sales_profile3,
            deposit_made=False
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
