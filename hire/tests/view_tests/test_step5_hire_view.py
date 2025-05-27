from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.messages import get_messages
from decimal import Decimal
import datetime
import uuid

# Import models
from hire.models import TempHireBooking
from dashboard.models import HireSettings

# Import model factories
from hire.tests.test_helpers.model_factories import (
    create_motorcycle,
    create_hire_settings,
    create_temp_hire_booking,
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
        self.core_index_url = reverse('core:index')

        # Ensure HireSettings exists
        self.hire_settings = create_hire_settings(
            deposit_enabled=True,
            deposit_percentage=Decimal('20.00'),
            enable_online_full_payment=True,
            enable_online_deposit_payment=True,
            enable_in_store_full_payment=True, # Ensure this is True for the test
            hire_pricing_strategy='24_hour_customer_friendly'
        )

        # Create a motorcycle for default bookings
        self.motorcycle = create_motorcycle(
            daily_hire_rate=Decimal('100.00'),
            hourly_hire_rate=Decimal('20.00')
        )

        # Common booking dates/times
        self.pickup_date = datetime.date.today() + datetime.timedelta(days=1)
        self.return_date = self.pickup_date + datetime.timedelta(days=2)
        self.pickup_time = datetime.time(9, 0)
        self.return_time = datetime.time(17, 0)

    def _create_and_set_temp_booking_in_session(self, motorcycle=None, pickup_date=None, pickup_time=None, return_date=None, return_time=None):
        """
        Helper to create a TempHireBooking and set its ID/UUID in the session.
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

        temp_booking = create_temp_hire_booking(
            motorcycle=motorcycle,
            pickup_date=pickup_date,
            pickup_time=pickup_time,
            return_date=return_date,
            return_time=return_time,
            total_hire_price=Decimal('100.00'), # Some initial price to avoid None
            grand_total=Decimal('100.00'),
            deposit_amount=Decimal('20.00'),
        )
        session = self.client.session
        session['temp_booking_id'] = temp_booking.id
        session['temp_booking_uuid'] = str(temp_booking.session_uuid)
        session.save()
        return temp_booking

    def _refresh_temp_booking(self):
        """Helper to refresh the temp_booking instance from the database."""
        # This might not be needed as often with the new helper
        pass

    # --- GET Request Tests ---

    def test_get_request_success_with_valid_session(self):
        """
        Test GET request with a valid temp_booking_uuid in session.
        """
        temp_booking = self._create_and_set_temp_booking_in_session()
        response = self.client.get(self.step5_url)

        self.assertEqual(response.status_code, 200)

        # Corrected template name as per user's instruction
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
        # This prevents the 'temp_booking' check from redirecting to step2_choose_bike
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
        self.assertRedirects(response, reverse('hire:step6_payment_details'))
        temp_booking.refresh_from_db()
        self.assertEqual(temp_booking.payment_option, 'online_full')

    def test_post_request_online_deposit_payment_redirects_to_payment_details(self):
        """
        Test POST request with 'online_deposit' payment option.
        """
        temp_booking = self._create_and_set_temp_booking_in_session()
        form_data = {'payment_method': 'online_deposit'}
        response = self.client.post(self.step5_url, form_data)
        self.assertRedirects(response, reverse('hire:step6_payment_details'))
        temp_booking.refresh_from_db()
        self.assertEqual(temp_booking.payment_option, 'online_deposit')
        
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
