from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.messages import get_messages
from decimal import Decimal
import datetime
import uuid

# Import models
from hire.models import TempHireBooking, HireBooking # Import HireBooking to check its creation
from dashboard.models import HireSettings

# Import model factories
from hire.tests.test_helpers.model_factories import (
    create_motorcycle,
    create_hire_settings,
    create_temp_hire_booking,
    create_hire_booking, # Import create_hire_booking
    create_driver_profile, # Import create_driver_profile
)

# Import pricing functions (now in hire.hire_pricing)
from hire.hire_pricing import calculate_booking_grand_total

class BookSumAndPaymentOptionsViewTest(TestCase):
    """
    Tests for the BookSumAndPaymentOptionsView (Step 5 of the hire booking process).
    """

    def setUp(self):
        """
        Set up common URLs and HireSettings.
        """
        self.client = Client()
        self.step5_url = reverse('hire:step5_summary_payment_options')
        self.step2_url = reverse('hire:step2_choose_bike')
        self.step6_url = reverse('hire:step6_payment_details') # Added for clarity
        self.step7_url_base = reverse('hire:step7_confirmation') # Base URL for step 7
        self.core_index_url = reverse('core:index')

        # Ensure HireSettings exists and payment options are enabled for testing
        self.hire_settings = create_hire_settings(
            deposit_enabled=True,
            deposit_percentage=Decimal('20.00'),
            enable_online_full_payment=True,
            enable_online_deposit_payment=True,
            enable_in_store_full_payment=True,
            hire_pricing_strategy='24_hour_customer_friendly'
        )

        # Create a motorcycle for default bookings
        self.motorcycle = create_motorcycle(
            daily_hire_rate=Decimal('100.00'),
            hourly_hire_rate=Decimal('20.00'),
            is_available=True, # Ensure motorcycle is available
            engine_size=125 # Set engine size to require license
        )
        # Create a driver profile to associate with bookings
        self.driver_profile = create_driver_profile()

        # Common booking dates/times
        self.pickup_date = datetime.date.today() + datetime.timedelta(days=1)
        self.return_date = self.pickup_date + datetime.timedelta(days=2)
        self.pickup_time = datetime.time(9, 0)
        self.return_time = datetime.time(17, 0)

    def _create_and_set_temp_booking_in_session(self, motorcycle=None, pickup_date=None, pickup_time=None, return_date=None, return_time=None, has_motorcycle_license=True, driver_profile=None):
        """
        Helper to create a TempHireBooking and set its ID/UUID in the session.
        Ensures valid dates/times and license for availability checks.
        """
        if motorcycle is None:
            motorcycle = self.motorcycle
        if pickup_date is None:
            pickup_date = self.pickup_date
        if pickup_time is None:
            pickup_time = self.pickup_time
        if return_date is None:
            return_date = self.return_date
        if return_time is None:
            return_time = self.return_time
        if driver_profile is None: # Ensure driver_profile is set
            driver_profile = self.driver_profile

        temp_booking = create_temp_hire_booking(
            motorcycle=motorcycle,
            pickup_date=pickup_date,
            pickup_time=pickup_time,
            return_date=return_date,
            return_time=return_time,
            total_hire_price=Decimal('100.00'), # Some initial price to avoid None
            grand_total=Decimal('100.00'),
            deposit_amount=Decimal('20.00'),
            has_motorcycle_license=has_motorcycle_license, # Ensure license is set for tests
            driver_profile=driver_profile, # Pass the driver profile
        )
        session = self.client.session
        session['temp_booking_id'] = temp_booking.id
        session['temp_booking_uuid'] = str(temp_booking.session_uuid)
        session.save()
        return temp_booking

    # --- GET Request Tests ---

    def test_get_request_success_with_valid_session(self):
        """
        Test GET request with a valid temp_booking_uuid in session.
        """
        temp_booking = self._create_and_set_temp_booking_in_session()
        response = self.client.get(self.step5_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hire/step5_book_sum_and_payment_options.html')
        self.assertEqual(response.context['temp_booking'].id, temp_booking.id)
        self.assertIn('hire_settings', response.context)
        self.assertIn('form', response.context)

    def test_get_request_no_temp_booking_uuid_in_session(self):
        """
        Test that a GET request without a temp_booking_uuid in session redirects
        and shows an error message.
        """
        response = self.client.get(self.step5_url)
        self.assertRedirects(response, self.step2_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Your booking session has expired. Please start again.")

    def test_get_request_invalid_temp_booking_id_uuid(self):
        """
        Test GET request with an invalid temp_booking_uuid in session.
        Should redirect and show an error message.
        """
        session = self.client.session
        session['temp_booking_id'] = 9999 # Non-existent ID
        session['temp_booking_uuid'] = str(uuid.uuid4()) # Random UUID
        session.save()

        response = self.client.get(self.step5_url)
        self.assertRedirects(response, self.step2_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Your booking session has expired. Please start again.")

    def test_get_request_no_hire_settings(self):
        """
        Test that a GET request when no HireSettings exist redirects.
        """
        # Ensure a valid temp_booking exists in session first
        self._create_and_set_temp_booking_in_session()

        # Now delete HireSettings
        HireSettings.objects.all().delete()

        response = self.client.get(self.step5_url)
        self.assertRedirects(response, self.core_index_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Hire settings not found.")

    # --- POST Request Tests ---

    def test_post_request_online_full_payment_redirects_to_payment_details(self):
        """
        Test POST request with 'online_full' payment option.
        """
        temp_booking = self._create_and_set_temp_booking_in_session()
        form_data = {'payment_method': 'online_full'}
        response = self.client.post(self.step5_url, form_data)
        self.assertRedirects(response, self.step6_url)
        temp_booking.refresh_from_db()
        self.assertEqual(temp_booking.payment_option, 'online_full')

    def test_post_request_online_deposit_payment_redirects_to_payment_details(self):
        """
        Test POST request with 'online_deposit' payment option.
        """
        temp_booking = self._create_and_set_temp_booking_in_session()
        form_data = {'payment_method': 'online_deposit'}
        response = self.client.post(self.step5_url, form_data)
        self.assertRedirects(response, self.step6_url)
        temp_booking.refresh_from_db()
        self.assertEqual(temp_booking.payment_option, 'online_deposit')

    def test_post_request_in_store_full_payment_redirects_to_confirmation(self):
        """
        Test POST request with 'in_store_full' payment option.
        Should create a HireBooking and redirect to step 7.
        """
        temp_booking = self._create_and_set_temp_booking_in_session()
        # Verify no HireBooking exists initially for this temp_booking's motorcycle
        self.assertEqual(HireBooking.objects.filter(motorcycle=temp_booking.motorcycle).count(), 0)

        form_data = {'payment_method': 'in_store_full'}
        response = self.client.post(self.step5_url, form_data)

        # EXPECTATION CHANGED: Expect redirection to step 7 without payment_intent_id
        self.assertRedirects(response, self.step7_url_base)

        # Verify TempHireBooking is deleted
        self.assertFalse(TempHireBooking.objects.filter(id=temp_booking.id).exists())

        # Verify a HireBooking was created
        hire_booking = HireBooking.objects.get(motorcycle=temp_booking.motorcycle, pickup_date=temp_booking.pickup_date)
        self.assertIsNotNone(hire_booking)
        self.assertEqual(hire_booking.payment_method, 'in_store')
        self.assertEqual(hire_booking.payment_status, 'pending_in_store')
        self.assertEqual(hire_booking.amount_paid, Decimal('0.00')) # No online payment for in-store

        # Check for success message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn("Your booking", str(messages[0]))
        self.assertIn("has been successfully created", str(messages[0]))
        self.assertIn("Please pay the full amount in-store at pickup", str(messages[0]))


    def test_post_request_invalid_form_renders_template_with_errors(self):
        """
        Test POST request with invalid form data.
        """
        self._create_and_set_temp_booking_in_session()
        form_data = {'payment_method': 'invalid_option'} # Invalid choice
        response = self.client.post(self.step5_url, form_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'hire/step5_book_sum_and_payment_options.html')
        # Access the form from the response context
        self.assertFormError(response.context['form'], 'payment_method', 'Select a valid choice. invalid_option is not one of the available choices.')

    def test_post_request_motorcycle_becomes_unavailable(self):
        """
        Test POST request when the motorcycle becomes unavailable just before finalization.
        Should redirect to step 2 with an error message.
        """
        temp_booking = self._create_and_set_temp_booking_in_session()

        # Simulate motorcycle becoming unavailable by creating an overlapping booking
        # Use the factory to create a HireBooking with the same motorcycle and overlapping dates/times
        create_hire_booking(
            motorcycle=self.motorcycle, # Use the same motorcycle as the temp_booking
            pickup_date=self.pickup_date,
            pickup_time=self.pickup_time,
            return_date=self.return_date,
            return_time=self.return_time,
            driver_profile=self.driver_profile, # Provide a driver_profile
            status='confirmed', # Ensure it's a conflicting status
        )

        form_data = {'payment_method': 'online_full'} # Doesn't matter which payment method is chosen
        response = self.client.post(self.step5_url, form_data)

        self.assertRedirects(response, self.step2_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn("The selected motorcycle is not available for your chosen dates/times due to an existing booking.", str(messages[0]))
        # Ensure temp_booking is NOT deleted if availability check fails
        self.assertTrue(TempHireBooking.objects.filter(id=temp_booking.id).exists())

    def test_post_request_no_motorcycle_license_for_large_engine(self):
        """
        Test POST request when the user does not have a motorcycle license
        but the selected motorcycle requires one.
        """
        # Create a temp booking without a motorcycle license
        temp_booking = self._create_and_set_temp_booking_in_session(has_motorcycle_license=False)
        # Ensure the motorcycle engine size is > 50 for this test
        self.motorcycle.engine_size = 125
        self.motorcycle.save()

        form_data = {'payment_method': 'online_full'}
        response = self.client.post(self.step5_url, form_data)

        self.assertRedirects(response, self.step2_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn("You require a full motorcycle license for this motorcycle.", str(messages[0]))
        self.assertTrue(TempHireBooking.objects.filter(id=temp_booking.id).exists())
