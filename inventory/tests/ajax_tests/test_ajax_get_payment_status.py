# inventory/tests/test_ajax/test_ajax_get_payment_status.py

from django.test import TestCase, Client
from django.urls import reverse
import json
from decimal import Decimal
import datetime

# Import models from your app
from inventory.models import SalesBooking
from payments.models import Payment

# Import your factories
from ..test_helpers.model_factories import (
    MotorcycleFactory,
    SalesProfileFactory,
    PaymentFactory,
    SalesBookingFactory,
)


class AjaxGetPaymentStatusTest(TestCase):
    """
    Tests for the AJAX endpoint `ajax_sales_payment_status_check`.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up test data for the GetPaymentStatusView AJAX endpoint.
        This includes:
        - A client for making HTTP requests.
        - A motorcycle, sales profile, and payment instances.
        - SalesBooking instances representing different payment/booking statuses.
        """
        cls.client = Client()

        # Create a common motorcycle and sales profile
        cls.motorcycle = MotorcycleFactory()
        cls.sales_profile = SalesProfileFactory()

        # Scenario 1: Successful SalesBooking and Payment
        cls.successful_payment = PaymentFactory(
            status='succeeded',
            amount=Decimal('100.00'),
            currency='AUD'
        )
        cls.successful_booking = SalesBookingFactory(
            motorcycle=cls.motorcycle,
            sales_profile=cls.sales_profile,
            payment=cls.successful_payment,
            stripe_payment_intent_id=cls.successful_payment.stripe_payment_intent_id,
            amount_paid=cls.successful_payment.amount,
            payment_status='paid',
            booking_status='confirmed',
            appointment_date=datetime.date.today(),
            appointment_time=datetime.time(10, 0, 0)
        )

        # Scenario 2: Payment exists but SalesBooking is not yet created (simulates webhook processing)
        cls.processing_payment = PaymentFactory(
            status='succeeded',
            amount=Decimal('50.00'),
            currency='AUD'
        )
        # No SalesBooking associated with this processing_payment yet.

        # Scenario 3: Neither Payment nor SalesBooking exists for a given intent ID
        cls.non_existent_payment_intent_id = "pi_nonexistent12345"

    def test_successful_payment_status_check(self):
        """
        Test that a successful payment intent ID returns 'ready' status
        and correct booking details.
        """
        response = self.client.get(
            reverse('inventory:ajax_sales_payment_status_check'),
            {'payment_intent_id': self.successful_booking.stripe_payment_intent_id}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['status'], 'ready')
        self.assertEqual(data['booking_reference'], self.successful_booking.sales_booking_reference)
        self.assertEqual(data['booking_status'], 'Confirmed')  # Display name
        self.assertEqual(data['payment_status'], 'paid')      # Display name
        self.assertEqual(Decimal(data['amount_paid']), self.successful_booking.amount_paid)
        self.assertEqual(data['currency'], self.successful_booking.currency)
        self.assertIn(str(self.motorcycle.year), data['motorcycle_details'])
        self.assertIn(self.motorcycle.brand, data['motorcycle_details'])
        self.assertIn(self.motorcycle.model, data['motorcycle_details'])
        self.assertEqual(data['customer_name'], self.sales_profile.name)
        self.assertEqual(data['appointment_date'], self.successful_booking.appointment_date.strftime('%d %b %Y'))
        self.assertEqual(data['appointment_time'], self.successful_booking.appointment_time.strftime('%I:%M %p'))

        # Verify session change
        self.assertIn('sales_booking_reference', self.client.session)
        self.assertEqual(self.client.session['sales_booking_reference'], self.successful_booking.sales_booking_reference)

    def test_payment_processing_status(self):
        """
        Test that if a payment exists but no sales booking, it returns 'processing'.
        This simulates a scenario where the webhook might still be finalizing the booking.
        """
        response = self.client.get(
            reverse('inventory:ajax_sales_payment_status_check'),
            {'payment_intent_id': self.processing_payment.stripe_payment_intent_id}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['status'], 'processing')
        self.assertIn('Booking finalization is still in progress.', data['message'])

    def test_payment_intent_not_found(self):
        """
        Test that if neither SalesBooking nor Payment exists for the ID, it returns 'error'.
        """
        response = self.client.get(
            reverse('inventory:ajax_sales_payment_status_check'),
            {'payment_intent_id': self.non_existent_payment_intent_id}
        )
        self.assertEqual(response.status_code, 500) # Should be 500 as per ajax_get_payment_status.py
        data = response.json()

        self.assertEqual(data['status'], 'error')
        self.assertIn('Booking finalization failed. Please contact support for assistance.', data['message'])

    def test_missing_payment_intent_id(self):
        """
        Test that if payment_intent_id is not provided, it returns a 400 error.
        """
        response = self.client.get(
            reverse('inventory:ajax_sales_payment_status_check')
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()

        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['message'], 'Payment Intent ID is required.')

    def test_sales_booking_details_in_response(self):
        """
        Ensure all relevant sales booking details are correctly included in the response.
        """
        response = self.client.get(
            reverse('inventory:ajax_sales_payment_status_check'),
            {'payment_intent_id': self.successful_booking.stripe_payment_intent_id}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn('booking_reference', data)
        self.assertIn('booking_status', data)
        self.assertIn('payment_status', data)
        self.assertIn('amount_paid', data)
        self.assertIn('currency', data)
        self.assertIn('motorcycle_details', data)
        self.assertIn('customer_name', data)
        self.assertIn('appointment_date', data)
        self.assertIn('appointment_time', data)

        self.assertEqual(data['booking_reference'], self.successful_booking.sales_booking_reference)
        self.assertEqual(data['booking_status'], self.successful_booking.get_booking_status_display())
        self.assertEqual(data['payment_status'], self.successful_booking.get_payment_status_display())
        self.assertEqual(Decimal(data['amount_paid']), self.successful_booking.amount_paid)
        self.assertEqual(data['currency'], self.successful_booking.currency)
        self.assertEqual(data['motorcycle_details'], f"{self.successful_booking.motorcycle.year} {self.successful_booking.motorcycle.brand} {self.successful_booking.motorcycle.model}")
        self.assertEqual(data['customer_name'], self.successful_booking.sales_profile.name)
        self.assertEqual(data['appointment_date'], self.successful_booking.appointment_date.strftime('%d %b %Y'))
        self.assertEqual(data['appointment_time'], self.successful_booking.appointment_time.strftime('%I:%M %p'))

