
from django.test import TestCase
from unittest.mock import patch
from inventory.utils.confirm_sales_booking import confirm_sales_booking
from inventory.tests.test_helpers.model_factories import SalesBookingFactory, MotorcycleFactory

class ConfirmSalesBookingTests(TestCase):

    def setUp(self):
        self.motorcycle = MotorcycleFactory(quantity=1, condition='new')
        self.sales_booking = SalesBookingFactory(motorcycle=self.motorcycle)

    @patch('inventory.utils.confirm_sales_booking.send_templated_email')
    def test_confirm_sales_booking_success(self, mock_send_email):
        self.motorcycle.condition = 'new'
        self.motorcycle.save()
        result = confirm_sales_booking(self.sales_booking.id)
        self.assertTrue(result['success'])
        self.assertEqual(result['message'], 'Sales booking confirmed successfully.')
        self.sales_booking.refresh_from_db()
        self.assertEqual(self.sales_booking.booking_status, 'confirmed')
        self.motorcycle.refresh_from_db()
        self.assertEqual(self.motorcycle.quantity, 0)
        self.assertFalse(self.motorcycle.is_available)
        self.assertEqual(self.motorcycle.status, 'sold')
        self.assertEqual(mock_send_email.call_count, 2)

    def test_confirm_sales_booking_not_found(self):
        result = confirm_sales_booking(999)
        self.assertFalse(result['success'])
        self.assertEqual(result['message'], 'Sales Booking not found.')

    def test_confirm_sales_booking_already_confirmed(self):
        self.sales_booking.booking_status = 'confirmed'
        self.sales_booking.save()
        result = confirm_sales_booking(self.sales_booking.id)
        self.assertFalse(result['success'])
        self.assertEqual(result['message'], 'Booking already confirmed or completed.')

    @patch('inventory.utils.confirm_sales_booking.send_templated_email')
    def test_confirm_sales_booking_used_motorcycle(self, mock_send_email):
        used_motorcycle = MotorcycleFactory(condition='used', is_available=True)
        used_booking = SalesBookingFactory(motorcycle=used_motorcycle)
        used_motorcycle.condition = 'used'
        used_motorcycle.save()
        result = confirm_sales_booking(used_booking.id)
        self.assertTrue(result['success'])
        used_booking.refresh_from_db()
        self.assertEqual(used_booking.booking_status, 'confirmed')
        used_motorcycle.refresh_from_db()
        self.assertFalse(used_motorcycle.is_available)
        self.assertEqual(used_motorcycle.status, 'reserved')
        self.assertEqual(mock_send_email.call_count, 2)
