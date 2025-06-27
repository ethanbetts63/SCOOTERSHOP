import datetime
from decimal import Decimal
import stripe
from unittest import skipIf, mock

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.conf import settings
from django.core import mail
from django.utils import timezone
from django.contrib.messages import get_messages

from inventory.models import TempSalesBooking, SalesBooking, SalesProfile, Motorcycle
from payments.models import Payment
from ..test_helpers.model_factories import (
    InventorySettingsFactory,
    MotorcycleFactory,
    UserFactory,
)
from payments.webhook_handlers.sales_handlers import handle_sales_booking_succeeded

@override_settings(ADMIN_EMAIL='ethan.betts.dev@gmail.com')
class TestEnquiryFlows(TestCase):
    """
    Tests for the enquiry-only flow (no deposit required).
    This simulates users who want to ask a question or book a viewing without a financial commitment.
    """

    def setUp(self):
        """Set up the basic environment for enquiry tests."""
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
        self.another_motorcycle = MotorcycleFactory(
            is_available=True, status='available', price=Decimal('8000.00')
        )

    def test_enquiry_with_appointment_flow(self):
        """
        Test a full enquiry flow where the user requests an appointment.
        This includes updating their profile details partway through.
        """
        initiate_url = reverse('inventory:initiate_booking', kwargs={'pk': self.motorcycle.pk})
        response = self.client.post(initiate_url, {'deposit_required_for_flow': 'false'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('temp_sales_booking_uuid', self.client.session)

        step1_url = reverse('inventory:step1_sales_profile')
        step2_url = reverse('inventory:step2_booking_details_and_appointment')
        
        # User fills out profile details for the first time
        profile_data = {'name': 'Enquiry User', 'email': 'enquiry@example.com', 'phone_number': '555-0000'}
        response = self.client.post(step1_url, profile_data)
        self.assertRedirects(response, step2_url)

        # User goes back and updates their profile details
        self.client.get(step1_url)
        updated_profile_data = {'name': 'Enquiry User Updated', 'email': 'enquiry@example.com', 'phone_number': '555-1111'}
        response = self.client.post(step1_url, updated_profile_data)
        self.assertRedirects(response, step2_url)

        # User fills out appointment details and confirms
        appointment_data = {
            'request_viewing': 'yes',
            'appointment_date': '2025-10-20',
            'appointment_time': '10:00',
            'terms_accepted': 'on',
            'customer_notes': 'I would like to come see this bike.'
        }
        response = self.client.post(step2_url, appointment_data)

        # Assert the final state after submission
        self.assertRedirects(response, reverse('inventory:step4_confirmation'))
        self.assertEqual(TempSalesBooking.objects.count(), 0) # Temp booking should be deleted
        self.assertEqual(SalesBooking.objects.count(), 1)   # Final booking should be created
        
        final_booking = SalesBooking.objects.first()
        self.assertEqual(final_booking.sales_profile.name, 'Enquiry User Updated')
        self.assertEqual(final_booking.sales_profile.phone_number, '555-1111')
        self.assertEqual(final_booking.payment_status, 'unpaid')
        self.assertIsNotNone(final_booking.appointment_date)
        
        confirmation_response = self.client.get(response.url)
        self.assertEqual(confirmation_response.status_code, 200)
        self.assertContains(confirmation_response, final_booking.sales_booking_reference)
        self.assertIn('last_sales_booking_timestamp', self.client.session)


    def test_enquiry_without_appointment_flow(self):
        """
        Test a full enquiry flow where the user only sends a message.
        This includes updating their profile details partway through.
        """
        initiate_url = reverse('inventory:initiate_booking', kwargs={'pk': self.motorcycle.pk})
        self.client.post(initiate_url, {'deposit_required_for_flow': 'false'})

        step1_url = reverse('inventory:step1_sales_profile')
        step2_url = reverse('inventory:step2_booking_details_and_appointment')
        
        profile_data = {'name': 'Message User', 'email': 'message@example.com', 'phone_number': '555-1111'}
        response = self.client.post(step1_url, profile_data)
        self.assertRedirects(response, step2_url)
        
        # User goes back and updates their profile
        self.client.get(step1_url)
        updated_profile_data = {'name': 'Message User Updated', 'email': 'message@example.com', 'phone_number': '555-2222'}
        response = self.client.post(step1_url, updated_profile_data)
        self.assertRedirects(response, step2_url)

        # User submits a message without an appointment
        enquiry_data = {
            'request_viewing': 'no',
            'terms_accepted': 'on',
            'customer_notes': 'Just wondering about the service history.'
        }
        response = self.client.post(step2_url, enquiry_data)

        # Assert the final state
        self.assertRedirects(response, reverse('inventory:step4_confirmation'))
        self.assertEqual(SalesBooking.objects.count(), 1)
        
        final_booking = SalesBooking.objects.first()
        self.assertEqual(final_booking.sales_profile.name, 'Message User Updated')
        self.assertEqual(final_booking.sales_profile.phone_number, '555-2222')
        self.assertEqual(final_booking.payment_status, 'unpaid')
        self.assertIsNone(final_booking.appointment_date)

        confirmation_response = self.client.get(response.url)
        self.assertEqual(confirmation_response.status_code, 200)
        self.assertIn('last_sales_booking_timestamp', self.client.session)


@skipIf(not settings.STRIPE_SECRET_KEY, "Stripe API key not configured in settings")
class TestDepositFlows(TestCase):
    """
    Tests for the deposit flow, which involves Stripe payments.
    These tests simulate complex user journeys, including changing their mind and restarting.
    """

    def setUp(self):
        """Set up the environment for deposit tests, including two motorcycles."""
        self.client = Client()
        self.user = UserFactory()
        self.client.force_login(self.user)
        self.settings = InventorySettingsFactory(
            enable_reservation_by_deposit=True,
            deposit_amount=Decimal('150.00'),
            currency_code='AUD'
        )
        self.motorcycle = MotorcycleFactory(
            is_available=True, price=Decimal('12000.00'), status='available',
            year=1999, brand='Kawasaki', model='Star'
        )
        # Add another motorcycle for the bike-switching test
        self.another_motorcycle = MotorcycleFactory(
            is_available=True, price=Decimal('15000.00'), status='available',
            year=2022, brand='Ducati', model='Panigale'
        )
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def test_deposit_flow_with_updates_and_bike_switch(self):
        """
        A comprehensive test where a logged-in user:
        1. Starts booking bike A.
        2. Updates their profile and appointment details.
        3. Reaches the payment page for bike A but abandons.
        4. Starts a new booking for bike B.
        5. Completes the payment for bike B.
        6. Verifies bike B is reserved and bike A is still available.
        """
        step1_url = reverse('inventory:step1_sales_profile')
        step2_url = reverse('inventory:step2_booking_details_and_appointment')
        step3_url = reverse('inventory:step3_payment')

        # --- User starts booking the FIRST bike ---
        initiate_url_1 = reverse('inventory:initiate_booking', kwargs={'pk': self.motorcycle.pk})
        self.client.post(initiate_url_1, {'deposit_required_for_flow': 'true'})
        
        # User fills out profile, goes back, and updates it
        profile_data = {'name': 'Thorough Tester', 'email': 'thorough.tester@example.com', 'phone_number': '555-1234'}
        self.client.post(step1_url, profile_data)
        self.client.get(step1_url)
        updated_profile_data = {'name': 'Thorough Tester Updated', 'email': 'thorough.tester@example.com', 'phone_number': '555-4321'}
        self.client.post(step1_url, updated_profile_data)
        
        # User fills out appointment, goes back, and updates it
        appointment_data = {'request_viewing': 'yes', 'appointment_date': '2025-09-15', 'appointment_time': '14:00', 'terms_accepted': 'on'}
        self.client.post(step2_url, appointment_data)
        self.client.get(step2_url)
        updated_appointment_data = {'request_viewing': 'yes', 'appointment_date': '2025-09-20', 'appointment_time': '09:00', 'terms_accepted': 'on'}
        self.client.post(step2_url, updated_appointment_data)
        
        # --- User reaches payment page for FIRST bike, then abandons ---
        self.client.get(step3_url)

        # --- User abandons and starts a NEW booking for a DIFFERENT bike ---
        initiate_url_2 = reverse('inventory:initiate_booking', kwargs={'pk': self.another_motorcycle.pk})
        self.client.post(initiate_url_2, {'deposit_required_for_flow': 'true'})
        
        # Check that the user's last updated profile data is pre-filled
        response = self.client.get(step1_url)
        self.assertContains(response, "Thorough Tester Updated")
        self.client.post(step1_url, updated_profile_data) 
        
        # User provides NEW appointment details for the NEW bike
        new_appointment_data = {'request_viewing': 'yes', 'appointment_date': '2025-11-01', 'appointment_time': '10:00', 'terms_accepted': 'on'}
        self.client.post(step2_url, new_appointment_data)
        
        # --- User completes payment for the NEW bike ---
        self.client.get(step3_url)
        temp_booking = TempSalesBooking.objects.get(session_uuid=self.client.session['temp_sales_booking_uuid'])
        payment_obj = Payment.objects.get(temp_sales_booking=temp_booking)
        payment_intent_id = payment_obj.stripe_payment_intent_id

        try:
            confirmation_url_path = reverse('inventory:step4_confirmation')
            full_return_url = f"http://testserver{confirmation_url_path}"
            stripe.PaymentIntent.confirm(payment_intent_id, payment_method="pm_card_visa", return_url=full_return_url)
        except stripe.error.StripeError as e:
            self.fail(f"Stripe API call failed during test: {e}")

        updated_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        handle_sales_booking_succeeded(payment_obj, updated_intent)

        # --- Assertions ---
        final_booking = SalesBooking.objects.get(motorcycle=self.another_motorcycle)
        self.assertEqual(final_booking.payment_status, 'deposit_paid')
        
        # Assert the booking is for the NEW motorcycle with the correct details
        self.assertEqual(final_booking.motorcycle, self.another_motorcycle)
        self.assertEqual(final_booking.sales_profile.name, 'Thorough Tester Updated')
        self.assertEqual(final_booking.appointment_date, datetime.date(2025, 11, 1))

        # Assert the original motorcycle was NOT reserved
        self.motorcycle.refresh_from_db()
        self.assertTrue(self.motorcycle.is_available)
        
        # Assert the NEW motorcycle IS reserved
        self.another_motorcycle.refresh_from_db()
        self.assertFalse(self.another_motorcycle.is_available)
        
        # Assert another user cannot initiate a booking for the reserved bike
        another_user_client = Client()
        another_user = UserFactory(username="another_user")
        another_user_client.force_login(another_user)
        details_url = reverse('inventory:motorcycle-detail', kwargs={'pk': self.another_motorcycle.pk})
        initiate_blocked_url = reverse('inventory:initiate_booking', kwargs={'pk': self.another_motorcycle.pk})
        response_blocked = another_user_client.post(initiate_blocked_url, follow=True)
        self.assertRedirects(response_blocked, details_url, status_code=302, target_status_code=200)

    def test_anonymous_deposit_with_restart_flow(self):
        """
        Test an anonymous user who starts a booking, abandons it, and then
        restarts the entire process from scratch for the same bike.
        This ensures that the old, orphaned booking doesn't interfere with the new one.
        """
        anon_client = Client()
        initiate_url = reverse('inventory:initiate_booking', kwargs={'pk': self.motorcycle.pk})
        step1_url = reverse('inventory:step1_sales_profile')
        step2_url = reverse('inventory:step2_booking_details_and_appointment')
        step3_url = reverse('inventory:step3_payment')

        # --- First attempt (abandoned) ---
        anon_client.post(initiate_url, {'deposit_required_for_flow': 'true'})
        profile_data = {'name': 'Guest User', 'email': 'guest.user@example.com', 'phone_number': '555-5678'}
        anon_client.post(step1_url, profile_data)
        appointment_data = {'request_viewing': 'yes', 'appointment_date': '2025-09-16', 'appointment_time': '11:00', 'terms_accepted': 'on'}
        anon_client.post(step2_url, appointment_data)
        anon_client.get(step3_url) # Reaches payment page and abandons

        # --- User abandons and restarts the whole process for the same bike ---
        # The original TempSalesBooking is now orphaned as the session key is replaced.
        anon_client.post(initiate_url, {'deposit_required_for_flow': 'true'})
        self.assertEqual(TempSalesBooking.objects.count(), 2) # There are now two temp bookings

        # --- User starts the form again with NEW details ---
        response = anon_client.get(step1_url)
        self.assertNotContains(response, 'Guest User') # Check that old data is NOT pre-filled for anonymous users
        
        new_profile_data = {'name': 'Restarted User', 'email': 'restarted.user@example.com', 'phone_number': '555-0000'}
        anon_client.post(step1_url, new_profile_data)
        
        new_appointment_data = {'request_viewing': 'yes', 'appointment_date': '2025-10-01', 'appointment_time': '16:00', 'terms_accepted': 'on'}
        anon_client.post(step2_url, new_appointment_data)

        # --- User completes payment on the second attempt ---
        anon_client.get(step3_url)
        self.assertEqual(Payment.objects.count(), 2) # We expect 2 payments as one is created for each abandoned flow
        
        # Get the latest payment object associated with the current session
        temp_booking = TempSalesBooking.objects.get(session_uuid=anon_client.session['temp_sales_booking_uuid'])
        payment_obj = Payment.objects.get(temp_sales_booking=temp_booking)
        payment_intent_id = payment_obj.stripe_payment_intent_id

        try:
            confirmation_url_path = reverse('inventory:step4_confirmation')
            full_return_url = f"http://testserver{confirmation_url_path}"
            stripe.PaymentIntent.confirm(payment_intent_id, payment_method="pm_card_visa", return_url=full_return_url)
        except stripe.error.StripeError as e:
            self.fail(f"Stripe API call failed during test: {e}")

        updated_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        handle_sales_booking_succeeded(payment_obj, updated_intent)
        
        # --- Assertions ---
        self.assertEqual(SalesBooking.objects.count(), 1)
        final_booking = SalesBooking.objects.first()
        self.assertEqual(final_booking.payment_status, 'deposit_paid')
        
        # Assert that the FINAL, RESTARTED details were saved
        self.assertEqual(final_booking.sales_profile.name, 'Restarted User')
        self.assertEqual(final_booking.sales_profile.phone_number, '555-0000')
        self.assertEqual(final_booking.appointment_date, datetime.date(2025, 10, 1))
        self.assertIsNone(final_booking.sales_profile.user) # Ensure no user is associated
        
        # Assert the motorcycle is now correctly marked as unavailable
        self.motorcycle.refresh_from_db()
        self.assertFalse(self.motorcycle.is_available)
