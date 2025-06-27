import datetime
import time
from decimal import Decimal
import stripe
from unittest import skipIf

from django.test import TestCase, Client
from django.urls import reverse
from django.conf import settings
from django.core import mail

from inventory.models import TempSalesBooking, SalesBooking, SalesProfile, Motorcycle
from payments.models import Payment
from ..test_helpers.model_factories import (
    InventorySettingsFactory,
    MotorcycleFactory,
    UserFactory,
    SalesProfileFactory,
)
from payments.webhook_handlers.sales_handlers import handle_sales_booking_succeeded

class TestNonDepositFlows(TestCase):
    """
    Tests for the sales booking process that do not involve payment
    and therefore do not require the Stripe API.
    """
    def setUp(self):
        """Set up the necessary objects for the test suite."""
        self.client = Client()
        self.user = UserFactory()
        self.client.force_login(self.user)
        self.settings = InventorySettingsFactory(currency_code='AUD')
        self.motorcycle = MotorcycleFactory(
            is_available=True,
            status='available',
            price=Decimal('5000.00'),
            year=1993,
            brand='Kawasaki',
            model='Enough'
        )

    def test_no_deposit_flow_with_appointment(self):
        """
        Tests the user flow for an enquiry with an appointment but no deposit.
        """
        # --- Step 0: Initiate Booking as a non-deposit enquiry ---
        initiate_url = reverse('inventory:initiate_booking', kwargs={'pk': self.motorcycle.pk})
        response = self.client.post(initiate_url, {'deposit_required_for_flow': 'false'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('temp_sales_booking_uuid', self.client.session)

        # --- Step 1: Submit Profile ---
        step1_url = reverse('inventory:step1_sales_profile')
        profile_data = {'name': 'Enquiry User', 'email': 'enquiry@example.com', 'phone_number': '555-0000'}
        response = self.client.post(step1_url, profile_data)
        self.assertRedirects(response, reverse('inventory:step2_booking_details_and_appointment'))

        # --- Step 2: Submit Appointment Details (no payment) ---
        step2_url = reverse('inventory:step2_booking_details_and_appointment')
        appointment_data = {
            'request_viewing': 'yes',
            'appointment_date': '2025-10-20',
            'appointment_time': '10:00',
            'terms_accepted': 'on',
            'customer_notes': 'I would like to come see this bike.'
        }
        response = self.client.post(step2_url, appointment_data)

        # --- Assert Final State ---
        self.assertRedirects(response, reverse('inventory:step4_confirmation'))
        self.assertEqual(TempSalesBooking.objects.count(), 0)
        self.assertEqual(SalesBooking.objects.count(), 1)
        
        final_booking = SalesBooking.objects.first()
        self.assertEqual(final_booking.payment_status, 'unpaid')
        self.assertEqual(final_booking.amount_paid, Decimal('0.00'))
        self.assertIsNotNone(final_booking.appointment_date)

        self.motorcycle.refresh_from_db()
        self.assertEqual(self.motorcycle.status, 'available')
        self.assertTrue(self.motorcycle.is_available)
        
        # --- Step 4: Check Confirmation Page ---
        confirmation_url = reverse('inventory:step4_confirmation')
        # We need to use the session to find the booking reference on the confirmation page
        response = self.client.get(confirmation_url)
        self.assertEqual(response.status_code, 200)
        # CORRECTED: Assert against the actual text in the template
        self.assertContains(response, "Thank you for your enquiry!")
        self.assertContains(response, final_booking.sales_booking_reference)

        self.assertEqual(len(mail.outbox), 2)
        self.assertIn('Your Motorcycle Appointment Request', mail.outbox[0].subject)
        self.assertIn('New Sales Enquiry (Online)', mail.outbox[1].subject)


    def test_no_deposit_flow_as_pure_enquiry(self):
        """
        Tests the user flow for a simple message enquiry with no appointment.
        """
        # --- Step 0: Initiate Booking as a non-deposit enquiry ---
        initiate_url = reverse('inventory:initiate_booking', kwargs={'pk': self.motorcycle.pk})
        self.client.post(initiate_url, {'deposit_required_for_flow': 'false'})

        # --- Step 1: Submit Profile ---
        step1_url = reverse('inventory:step1_sales_profile')
        profile_data = {'name': 'Message User', 'email': 'message@example.com', 'phone_number': '555-1111'}
        self.client.post(step1_url, profile_data)

        # --- Step 2: Submit Message only (no appointment) ---
        step2_url = reverse('inventory:step2_booking_details_and_appointment')
        enquiry_data = {
            'request_viewing': 'no',
            'terms_accepted': 'on',
            'customer_notes': 'Just wondering about the service history.'
        }
        response = self.client.post(step2_url, enquiry_data)

        # --- Assert Final State ---
        self.assertRedirects(response, reverse('inventory:step4_confirmation'))
        self.assertEqual(SalesBooking.objects.count(), 1)
        
        final_booking = SalesBooking.objects.first()
        self.assertEqual(final_booking.payment_status, 'unpaid')
        self.assertIsNone(final_booking.appointment_date)
        self.assertEqual(final_booking.customer_notes, 'Just wondering about the service history.')

        self.motorcycle.refresh_from_db()
        self.assertEqual(self.motorcycle.status, 'available')

        # --- Step 4: Check Confirmation Page ---
        confirmation_url = reverse('inventory:step4_confirmation')
        response = self.client.get(confirmation_url)
        self.assertEqual(response.status_code, 200)
        # CORRECTED: Assert against the actual text in the template
        self.assertContains(response, "Thank you for your enquiry!")

        self.assertEqual(len(mail.outbox), 2)
        self.assertIn('Your Motorcycle Enquiry Received', mail.outbox[0].subject)
        self.assertIn('New Sales Enquiry (Online)', mail.outbox[1].subject)


# This decorator will skip the test if a Stripe secret key is not configured
@skipIf(not settings.STRIPE_SECRET_KEY, "Stripe API key not configured in settings")
class TestSalesBookingE2EWithRealAPI(TestCase):
    """
    End-to-end tests for the multi-step sales booking process using the
    real Stripe test API to ensure integration is working.
    """

    def setUp(self):
        """Set up the necessary objects for the test suite."""
        self.client = Client()
        self.user = UserFactory()
        self.client.force_login(self.user)
        self.settings = InventorySettingsFactory(
            enable_reservation_by_deposit=True,
            deposit_amount=Decimal('150.00'),
            currency_code='AUD'
        )
        self.motorcycle = MotorcycleFactory(
            is_available=True,
            price=Decimal('12000.00'),
            status='available',
            year=1999,
            brand='Kawasaki',
            model='Star'
        )
        # Set the Stripe API key for this test
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def test_full_booking_flow_with_real_stripe_payment(self):
        """
        Tests the entire user flow making a real payment confirmation call
        to the Stripe test API.
        """
        # --- Step 0 & 1: Initiate Booking and Profile ---
        initiate_url = reverse('inventory:initiate_booking', kwargs={'pk': self.motorcycle.pk})
        self.client.post(initiate_url, {'deposit_required_for_flow': 'true'})
        
        step1_url = reverse('inventory:step1_sales_profile')
        profile_data = {'name': 'Test User', 'email': 'test@example.com', 'phone_number': '123'}
        self.client.post(step1_url, profile_data)
        
        # --- Step 2: Submit Appointment Details ---
        step2_url = reverse('inventory:step2_booking_details_and_appointment')
        appointment_data = {'request_viewing': 'yes', 'appointment_date': '2025-08-01', 'appointment_time': '11:00', 'terms_accepted': 'on'}
        response = self.client.post(step2_url, appointment_data)
        self.assertRedirects(response, reverse('inventory:step3_payment'))

        # --- Step 3: Load Payment Page & Make Real API Call ---
        step3_url = reverse('inventory:step3_payment')
        response = self.client.get(step3_url)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(Payment.objects.count(), 1)
        payment_obj = Payment.objects.first()
        payment_intent_id = payment_obj.stripe_payment_intent_id
        self.assertIsNotNone(payment_intent_id)

        # ** MAKE REAL STRIPE API CALL **
        try:
            confirmation_url_path = reverse('inventory:step4_confirmation')
            full_return_url = f"http://testserver{confirmation_url_path}"
            stripe.PaymentIntent.confirm(
                payment_intent_id,
                payment_method="pm_card_visa",
                return_url=full_return_url,
            )
        except stripe.error.StripeError as e:
            self.fail(f"Stripe API call failed during test: {e}")

        # ** SIMULATE THE WEBHOOK ARRIVING **
        updated_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        handle_sales_booking_succeeded(payment_obj, updated_intent)

        # --- Assert Final State ---
        self.assertEqual(TempSalesBooking.objects.count(), 0)
        self.assertEqual(SalesBooking.objects.count(), 1)
        
        final_booking = SalesBooking.objects.first()
        self.assertEqual(final_booking.payment_status, 'deposit_paid')
        self.motorcycle.refresh_from_db()
        self.assertEqual(self.motorcycle.status, 'reserved')

        # --- Step 4: User is Redirected to Confirmation ---
        confirmation_url = reverse('inventory:step4_confirmation') + f'?payment_intent_id={payment_intent_id}'
        response = self.client.get(confirmation_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, final_booking.sales_booking_reference)
        self.assertNotContains(response, "Your booking is currently being finalized")

    def test_full_booking_flow_with_thorough_checks(self):
        """
        Tests the entire user flow with detailed checks at each step, including
        database state and session data, and makes a real payment confirmation
        call to the Stripe test API.
        """
        # --- Step 0: Initiate Booking ---
        initiate_url = reverse('inventory:initiate_booking', kwargs={'pk': self.motorcycle.pk})
        response = self.client.post(initiate_url, {'deposit_required_for_flow': 'true'})
        
        # Assertions for Step 0
        self.assertEqual(response.status_code, 302)
        self.assertIn('temp_sales_booking_uuid', self.client.session)
        self.assertEqual(TempSalesBooking.objects.count(), 1)
        temp_booking = TempSalesBooking.objects.first()
        self.assertEqual(temp_booking.motorcycle, self.motorcycle)
        self.assertTrue(temp_booking.deposit_required_for_flow)

        # --- Step 1: Submit Profile ---
        step1_url = reverse('inventory:step1_sales_profile')
        profile_data = {
            'name': 'Thorough Tester',
            'email': 'thorough.tester@example.com',
            'phone_number': '555-1234'
        }
        response = self.client.post(step1_url, profile_data)

        # Assertions for Step 1
        self.assertRedirects(response, reverse('inventory:step2_booking_details_and_appointment'))
        temp_booking.refresh_from_db()
        self.assertIsNotNone(temp_booking.sales_profile)
        self.assertEqual(temp_booking.sales_profile.name, 'Thorough Tester')
        self.assertEqual(SalesProfile.objects.count(), 1)
        
        # --- Step 2: Submit Appointment Details ---
        step2_url = reverse('inventory:step2_booking_details_and_appointment')
        appointment_data = {
            'request_viewing': 'yes',
            'appointment_date': '2025-09-15',
            'appointment_time': '14:00',
            'terms_accepted': 'on'
        }
        response = self.client.post(step2_url, appointment_data)

        # Assertions for Step 2
        self.assertRedirects(response, reverse('inventory:step3_payment'))
        temp_booking.refresh_from_db()
        self.assertEqual(temp_booking.appointment_date, datetime.date(2025, 9, 15))
        self.assertEqual(temp_booking.appointment_time, datetime.time(14, 0))
        self.assertTrue(temp_booking.terms_accepted)

        # --- Step 3: Load Payment Page & Make Real API Call ---
        step3_url = reverse('inventory:step3_payment')
        response = self.client.get(step3_url)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(Payment.objects.count(), 1)
        payment_obj = Payment.objects.first()
        self.assertEqual(payment_obj.amount, self.settings.deposit_amount)
        self.assertEqual(payment_obj.temp_sales_booking, temp_booking)
        payment_intent_id = payment_obj.stripe_payment_intent_id
        self.assertIsNotNone(payment_intent_id)

        # ** MAKE REAL STRIPE API CALL **
        try:
            confirmation_url_path = reverse('inventory:step4_confirmation')
            full_return_url = f"http://testserver{confirmation_url_path}"
            stripe.PaymentIntent.confirm(
                payment_intent_id,
                payment_method="pm_card_visa",
                return_url=full_return_url,
            )
        except stripe.error.StripeError as e:
            self.fail(f"Stripe API call failed during test: {e}")

        # ** SIMULATE THE WEBHOOK ARRIVING **
        updated_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        handle_sales_booking_succeeded(payment_obj, updated_intent)

        # --- Assert Final State ---
        self.assertEqual(TempSalesBooking.objects.count(), 0)
        self.assertEqual(SalesBooking.objects.count(), 1)
        
        final_booking = SalesBooking.objects.first()
        self.assertEqual(final_booking.payment_status, 'deposit_paid')
        self.assertEqual(final_booking.amount_paid, self.settings.deposit_amount)
        self.assertEqual(final_booking.sales_profile.name, 'Thorough Tester')
        self.assertEqual(final_booking.appointment_date, datetime.date(2025, 9, 15))

        self.motorcycle.refresh_from_db()
        self.assertEqual(self.motorcycle.status, 'reserved')
        self.assertFalse(self.motorcycle.is_available)
        
        payment_obj.refresh_from_db()
        self.assertEqual(payment_obj.status, 'succeeded')
        self.assertEqual(payment_obj.sales_booking, final_booking)

        # --- Step 4: User is Redirected to Confirmation ---
        confirmation_url = reverse('inventory:step4_confirmation') + f'?payment_intent_id={payment_intent_id}'
        response = self.client.get(confirmation_url)

        # Assertions for confirmation page
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, final_booking.sales_booking_reference)
        self.assertContains(response, "Your deposit has been confirmed!")
        self.assertContains(response, "Amount Paid:")
        self.assertContains(response, f"{self.settings.deposit_amount}")
        self.assertContains(response, self.settings.currency_code)
        self.assertNotContains(response, "Your booking is currently being finalized")
