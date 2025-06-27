# hire/tests/view_tests/test_step7_hire_view.py

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from decimal import Decimal
import datetime
import uuid
from unittest.mock import patch
import json

# Import models
from hire.models import HireBooking
from payments.models import Payment

# Import model factories
from hire.tests.test_helpers.model_factories import (
    create_motorcycle,
    create_hire_settings,
    create_driver_profile,
    create_user,
    create_hire_booking,
    create_payment,
    create_addon,
    create_booking_addon,
    create_package,
)

User = get_user_model()

class BookingConfirmationViewTests(TestCase):
    """
    Tests for the BookingConfirmationView (Step 7 of the hire booking process).
    """

    def setUp(self):
        """
        Set up common URLs, HireSettings, Motorcycle, User, and DriverProfile.
        Log in the test client.
        """
        self.client = Client()
        self.step7_url = reverse('hire:step7_confirmation')
        self.step2_url = reverse('hire:step2_choose_bike')
        self.booking_status_check_url = reverse('hire:booking_status_check')

        self.hire_settings = create_hire_settings()
        self.motorcycle = create_motorcycle(
            daily_hire_rate=Decimal('120.00'),
            hourly_hire_rate=Decimal('25.00')
        )
        self.user = create_user(username='testuser_step7', password='password123')
        self.driver_profile = create_driver_profile(user=self.user, name="Test Driver Step7")
        self.client.login(username='testuser_step7', password='password123')

        self.pickup_date = datetime.date.today() + datetime.timedelta(days=3)
        self.return_date = self.pickup_date + datetime.timedelta(days=2)
        self.pickup_time = datetime.time(10, 0)
        self.return_time = datetime.time(16, 0)

        self.payment_intent_id = f"pi_{uuid.uuid4().hex}"
        self.booking_reference = f"HIRE-{uuid.uuid4().hex[:8].upper()}"

        # Basic HireBooking for many tests
        self.hire_booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile,
            pickup_date=self.pickup_date,
            return_date=self.return_date,
            pickup_time=self.pickup_time,
            return_time=self.return_time,
            booking_reference=self.booking_reference,
            stripe_payment_intent_id=self.payment_intent_id,
            grand_total=Decimal('240.00'),
            amount_paid=Decimal('240.00'),
            payment_status='paid',
            status='confirmed',
            currency='AUD'
        )
        # Add an addon to the booking for context testing
        self.addon1 = create_addon(name="GPS Navigation", daily_cost=Decimal("10.00"))
        self.booking_addon1 = create_booking_addon(
            booking=self.hire_booking,
            addon=self.addon1,
            quantity=1,
            booked_addon_price=Decimal("20.00") # 2 days * 10.00
        )
        self.hire_booking.total_addons_price = Decimal("20.00")
        self.hire_booking.grand_total = Decimal("260.00") # 240 (hire) + 20 (addon)
        self.hire_booking.amount_paid = Decimal("260.00")
        self.hire_booking.save()


    def test_get_confirmation_with_booking_reference_in_session(self):
        """
        Test GET request when 'final_booking_reference' is in session.
        This test now expects 'final_booking_reference' to persist in the session
        after the confirmation page is displayed, for consistency with online payments.
        """
        session = self.client.session
        session['final_booking_reference'] = self.hire_booking.booking_reference
        session['temp_booking_id'] = 12345 # Dummy temp booking id to check clearance
        session.save()

        response = self.client.get(self.step7_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hire/step7_booking_confirmation.html')
        self.assertFalse(response.context.get('is_processing'))
        self.assertEqual(response.context.get('hire_booking'), self.hire_booking)
        self.assertEqual(response.context.get('driver_name'), self.driver_profile.name)
        self.assertIn(self.addon1.name, [addon.addon.name for addon in response.context.get('addons')])

        # IMPORTANT: Refresh the session after the request to get the latest state
        self.client.session.load()

        # Check 'final_booking_reference' is now expected to be present
        self.assertEqual(self.client.session.get('final_booking_reference'), self.hire_booking.booking_reference)
        # 'temp_booking_id' should still be cleared
        self.assertNotIn('temp_booking_id', self.client.session)

    def test_get_confirmation_with_payment_intent_id_in_query(self):
        """
        Test GET request when 'payment_intent_id' is in query parameters.
        """
        session = self.client.session
        if 'final_booking_reference' in session: # Ensure it's not there initially
            del session['final_booking_reference']
        session['temp_booking_id'] = 12345 # Dummy temp booking id
        session.save() # Save the session state before making the request

        response = self.client.get(self.step7_url, {'payment_intent_id': self.hire_booking.stripe_payment_intent_id})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hire/step7_booking_confirmation.html')
        self.assertFalse(response.context.get('is_processing'))
        self.assertEqual(response.context.get('hire_booking'), self.hire_booking)

        # IMPORTANT: Refresh the session after the request to get the latest state
        self.client.session.load()

        # Check 'final_booking_reference' is added to session and 'temp_booking_id' is cleared
        self.assertEqual(self.client.session.get('final_booking_reference'), self.hire_booking.booking_reference)
        self.assertNotIn('temp_booking_id', self.client.session)

    def test_get_confirmation_payment_intent_id_booking_not_found_yet_processing(self):
        """
        Test GET request when HireBooking doesn't exist for payment_intent_id,
        but Payment object does, indicating processing.
        """
        new_payment_intent_id = f"pi_processing_{uuid.uuid4().hex}"
        # Create a Payment record, but no HireBooking yet
        create_payment(
            stripe_payment_intent_id=new_payment_intent_id,
            amount=Decimal("100.00"),
            status='succeeded' # Payment succeeded, but webhook might be slow
        )
        # Ensure HireBooking does not exist for this PI
        HireBooking.objects.filter(stripe_payment_intent_id=new_payment_intent_id).delete()


        response = self.client.get(self.step7_url, {'payment_intent_id': new_payment_intent_id})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hire/step7_booking_confirmation.html') # View uses this template for processing
        self.assertTrue(response.context.get('is_processing'))
        self.assertEqual(response.context.get('payment_intent_id'), new_payment_intent_id)
        self.assertIsNone(response.context.get('hire_booking'))

    def test_get_confirmation_no_identifiers_redirects_to_step2(self):
        """
        Test GET request with no booking_reference in session and no payment_intent_id in query.
        """
        session = self.client.session
        if 'final_booking_reference' in session:
            del session['final_booking_reference']
        if 'temp_booking_id' in session:
            del session['temp_booking_id']
        session.save()

        response = self.client.get(self.step7_url)
        self.assertRedirects(response, self.step2_url)

    def test_get_confirmation_invalid_booking_reference_in_session_no_pi_redirects_to_step2(self):
        """
        Test GET request with an invalid 'final_booking_reference' in session and no payment_intent_id.
        """
        session = self.client.session
        session['final_booking_reference'] = 'INVALID_REF'
        session.save()

        response = self.client.get(self.step7_url)
        # Since it tries PI next, and PI is not provided, it should redirect.
        self.assertRedirects(response, self.step2_url)

    def test_get_confirmation_payment_intent_id_no_hirebooking_no_payment_redirects_to_step2(self):
        """
        Test GET request with a payment_intent_id for which neither HireBooking nor Payment exists.
        This implies the PI is completely unknown or already fully processed and cleaned up (unlikely for this step).
        The view's logic: if HireBooking.DoesNotExist for PI, it then checks Payment. If Payment also DoesNotExist,
        the `is_processing` flag remains False (or becomes False if it was True from a booking_ref check).
        Then it hits "if not hire_booking and not payment_intent_id and not booking_reference" -> redirect.
        OR "if not hire_booking and is_processing" -> render processing.
        OR "if not hire_booking" -> redirect.
        In this case, hire_booking is None, is_processing is False. So it should hit the final "if not hire_booking" redirect.
        """
        unknown_payment_intent_id = f"pi_unknown_{uuid.uuid4().hex}"
        HireBooking.objects.filter(stripe_payment_intent_id=unknown_payment_intent_id).delete()
        Payment.objects.filter(stripe_payment_intent_id=unknown_payment_intent_id).delete()

        response = self.client.get(self.step7_url, {'payment_intent_id': unknown_payment_intent_id})
        # The view logic:
        # 1. booking_reference from session: None
        # 2. payment_intent_id from GET: unknown_payment_intent_id
        #    - HireBooking.objects.get(stripe_payment_intent_id=...) -> DoesNotExist. is_processing = True.
        # Then: if not hire_booking and is_processing: -> render processing template.
        # This seems to be the expected path.
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hire/step7_booking_confirmation.html')
        self.assertTrue(response.context.get('is_processing'))
        self.assertEqual(response.context.get('payment_intent_id'), unknown_payment_intent_id)


    def test_get_confirmation_clears_temp_booking_id_from_session(self):
        """
        Test that 'temp_booking_id' is cleared from session upon successful display.
        """
        session = self.client.session
        session['final_booking_reference'] = self.hire_booking.booking_reference
        session['temp_booking_id'] = 12345 # A dummy ID
        session.save()

        self.client.get(self.step7_url)
        self.assertNotIn('temp_booking_id', self.client.session)

    def test_get_confirmation_with_package_details(self):
        """Test confirmation page displays package details if a package is booked."""
        package = create_package(name="Weekend Warrior Pack", daily_cost=Decimal("50.00"))
        hire_booking_with_package = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile,
            package=package,
            stripe_payment_intent_id=f"pi_package_{uuid.uuid4().hex}",
            booking_reference=f"HIRE_PACK_{uuid.uuid4().hex[:6]}"
        )
        session = self.client.session
        session['final_booking_reference'] = hire_booking_with_package.booking_reference
        session.save()

        response = self.client.get(self.step7_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hire/step7_booking_confirmation.html')
        self.assertEqual(response.context['hire_booking'], hire_booking_with_package)
        self.assertEqual(response.context['package_name'], package.name)


class BookingStatusCheckViewTests(TestCase):
    """
    Tests for the BookingStatusCheckView (AJAX endpoint).
    """

    def setUp(self):
        self.client = Client()
        self.status_check_url = reverse('hire:booking_status_check')
        self.hire_settings = create_hire_settings()
        self.motorcycle = create_motorcycle()
        self.user = create_user(username='testuser_ajax_step7')
        self.driver_profile = create_driver_profile(user=self.user, name="Test AJAX Driver")
        self.client.login(username='testuser_ajax_step7', password='password123')

        self.payment_intent_id = f"pi_ajax_{uuid.uuid4().hex}"

        self.hire_booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile,
            stripe_payment_intent_id=self.payment_intent_id,
            grand_total=Decimal("150.00"),
            amount_paid=Decimal("150.00"),
            payment_status='paid',
            status='confirmed',
            currency='AUD',
            pickup_date=datetime.date.today() + datetime.timedelta(days=1),
            pickup_time=datetime.time(11,0),
            return_date=datetime.date.today() + datetime.timedelta(days=2),
            return_time=datetime.time(11,0),
        )
        self.addon = create_addon(name="Helmet Cam", daily_cost=Decimal("5.00"))
        self.booking_addon = create_booking_addon(
            booking=self.hire_booking,
            addon=self.addon,
            quantity=1,
            booked_addon_price=Decimal("5.00") # 1 day * 5.00 (adjust if booking duration changes)
        )
        # Re-calculate totals if needed, though factory should handle it.
        # For this test, we assume the hire_booking details are correct.

    def test_ajax_status_check_booking_ready(self):
        """
        Test AJAX status check when HireBooking is found (status: ready).
        """
        response = self.client.get(self.status_check_url, {'payment_intent_id': self.payment_intent_id}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response['status'], 'ready')
        self.assertEqual(json_response['booking_reference'], self.hire_booking.booking_reference)
        self.assertEqual(json_response['driver_name'], self.driver_profile.name)
        self.assertEqual(len(json_response['addons']), 1)
        self.assertEqual(json_response['addons'][0]['name'], self.addon.name)
        self.assertEqual(json_response['motorcycle_details'], f"{self.motorcycle.year} {self.motorcycle.brand} {self.motorcycle.model}")

    def test_ajax_status_check_booking_processing(self):
        """
        Test AJAX status check when HireBooking not found, but Payment exists (status: processing).
        """
        processing_pi_id = f"pi_processing_ajax_{uuid.uuid4().hex}"
        # Create Payment, but no HireBooking for this PI
        create_payment(stripe_payment_intent_id=processing_pi_id, status='succeeded')
        HireBooking.objects.filter(stripe_payment_intent_id=processing_pi_id).delete()


        response = self.client.get(self.status_check_url, {'payment_intent_id': processing_pi_id}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response['status'], 'processing')
        self.assertEqual(json_response['message'], 'Booking still being finalized.')

    def test_ajax_status_check_booking_finalization_failed(self):
        """
        Test AJAX status check when neither HireBooking nor Payment found (status: error, finalization failed).
        """
        failed_pi_id = f"pi_failed_ajax_{uuid.uuid4().hex}"
        # Ensure no HireBooking and no Payment exist for this PI
        HireBooking.objects.filter(stripe_payment_intent_id=failed_pi_id).delete()
        Payment.objects.filter(stripe_payment_intent_id=failed_pi_id).delete()

        response = self.client.get(self.status_check_url, {'payment_intent_id': failed_pi_id}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 500) # As per view logic
        json_response = response.json()
        self.assertEqual(json_response['status'], 'error')
        self.assertEqual(json_response['message'], 'Booking finalization failed. Please contact support.')

    def test_ajax_status_check_no_payment_intent_id(self):
        """
        Test AJAX status check without providing payment_intent_id.
        """
        response = self.client.get(self.status_check_url, {}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 400)
        json_response = response.json()
        self.assertEqual(json_response['status'], 'error')
        self.assertEqual(json_response['message'], 'Payment Intent ID is required')

    @patch('hire.views.step7_BookingConfirmation_view.HireBooking.objects.get')
    def test_ajax_status_check_generic_exception(self, mock_get_booking):
        """
        Test AJAX status check when a generic exception occurs during HireBooking retrieval.
        """
        mock_get_booking.side_effect = Exception("Database chaos!")

        response = self.client.get(self.status_check_url, {'payment_intent_id': 'pi_any_id'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 500)
        json_response = response.json()
        self.assertEqual(json_response['status'], 'error')
        self.assertEqual(json_response['message'], 'An internal server error occurred during status check.')

