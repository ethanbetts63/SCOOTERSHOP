from django.test import TestCase
from unittest.mock import patch
from service.utils.confirm_service_booking import confirm_service_booking
from service.tests.test_helpers.model_factories import ServiceBookingFactory, SiteSettingsFactory

class ConfirmServiceBookingTests(TestCase):

    def setUp(self):
        self.service_booking = ServiceBookingFactory(booking_status='pending')
        SiteSettingsFactory()

    @patch('mailer.utils.send_templated_email')
    def test_confirm_service_booking_success(self, mock_send_email):
        result = confirm_service_booking(self.service_booking.id)
        self.assertTrue(result['success'])
        self.assertEqual(result['message'], 'Service booking confirmed successfully.')
        self.service_booking.refresh_from_db()
        self.assertEqual(self.service_booking.booking_status, 'confirmed')
        self.assertEqual(mock_send_email.call_count, 2)

    def test_confirm_service_booking_not_found(self):
        result = confirm_service_booking(999)
        self.assertFalse(result['success'])
        self.assertEqual(result['message'], 'Service Booking not found.')

    def test_confirm_service_booking_already_confirmed(self):
        self.service_booking.booking_status = 'confirmed'
        self.service_booking.save()
        result = confirm_service_booking(self.service_booking.id)
        self.assertFalse(result['success'])
        self.assertEqual(result['message'], 'Booking already confirmed, in progress, or completed.')

    @patch('mailer.utils.send_templated_email')
    def test_confirm_service_booking_no_notification(self, mock_send_email):
        result = confirm_service_booking(self.service_booking.id, send_notification=False)
        self.assertTrue(result['success'])
        self.service_booking.refresh_from_db()
        self.assertEqual(self.service_booking.booking_status, 'confirmed')
        self.assertEqual(mock_send_email.call_count, 0)
