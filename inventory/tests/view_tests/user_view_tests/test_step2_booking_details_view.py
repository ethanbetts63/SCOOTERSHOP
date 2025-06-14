# inventory/tests/test_views/test_step2_booking_details_view.py

import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.messages import get_messages
from unittest import mock
import json
from decimal import Decimal

from inventory.models import TempSalesBooking, InventorySettings, SalesBooking, SalesProfile
from inventory.forms.sales_booking_appointment_form import BookingAppointmentForm
from inventory.utils.get_sales_appointment_date_info import get_sales_appointment_date_info
from inventory.utils.convert_temp_sales_booking import convert_temp_sales_booking # Import the utility for mocking

from ...test_helpers.model_factories import (
    TempSalesBookingFactory,
    InventorySettingsFactory,
    MotorcycleFactory,
    SalesProfileFactory,
    SalesBookingFactory
)

class Step2BookingDetailsViewTest(TestCase):
    """
    Tests for the Step2BookingDetailsView.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up common data for all tests in this class.
        """
        cls.client = Client()
        cls.url = reverse('inventory:step2_booking_details_and_appointment')

        # Ensure a singleton InventorySettings instance exists
        cls.inventory_settings = InventorySettingsFactory(
            enable_viewing_for_enquiry=True, # Ensure this is true for testing request_viewing
            enable_reservation_by_deposit=True, # Used to control temp_booking creation
        )

        # Create a dummy motorcycle for TempSalesBookingFactory
        cls.motorcycle = MotorcycleFactory()
        cls.sales_profile = SalesProfileFactory() # Create a default sales profile

    def _create_temp_booking_in_session(self, client, **kwargs):
        """
        Helper to create a TempSalesBooking and set its session_uuid (as string) in the session.
        Allows overriding temp_booking fields via kwargs.
        """
        default_kwargs = {
            'motorcycle': self.motorcycle,
            'sales_profile': self.sales_profile,
            'booking_status': 'pending_details',
            # Set deposit_required_for_flow on the TempSalesBooking instance directly
            'deposit_required_for_flow': self.inventory_settings.enable_reservation_by_deposit,
            'request_viewing': False,
            'appointment_date': None,
            'appointment_time': None,
            'customer_notes': '',
            'terms_accepted': False,
        }
        # Update defaults with any provided kwargs
        default_kwargs.update(kwargs)

        temp_booking = TempSalesBookingFactory(**default_kwargs)
        session = client.session
        session['temp_sales_booking_uuid'] = str(temp_booking.session_uuid)
        session.save()
        return temp_booking

    # --- GET Request Tests ---

    def test_get_no_temp_booking_id_in_session(self):
        """
        Test GET request when 'temp_sales_booking_uuid' is not in session.
        Should redirect to 'core:index' with an error message.
        """
        response = self.client.get(self.url, follow=True)
        self.assertRedirects(response, reverse('core:index'))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Your booking session has expired or is invalid. Please start again.")

    def test_get_invalid_temp_booking_id(self):
        """
        Test GET request with an invalid 'temp_sales_booking_uuid' in session.
        Should redirect to 'core:index' with an error message.
        """
        session = self.client.session
        session['temp_sales_booking_uuid'] = 'a2b3c4d5-e6f7-8901-2345-67890abcdef0' # Invalid UUID
        session.save()

        response = self.client.get(self.url, follow=True)
        self.assertRedirects(response, reverse('core:index'))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn("Your booking session could not be found or is invalid.", str(messages[0]))

    def test_get_no_inventory_settings(self):
        """
        Test GET request when no InventorySettings exist.
        Should redirect to 'core:index' with an error message.
        """
        self._create_temp_booking_in_session(self.client)
        InventorySettings.objects.all().delete() # Delete settings AFTER temp booking is in session
        self.assertFalse(InventorySettings.objects.exists()) # Verify deletion

        response = self.client.get(self.url, follow=True)
        self.assertRedirects(response, reverse('core:index'))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Inventory settings are not configured. Please contact support.")

        # Recreate settings for other tests
        self.inventory_settings = InventorySettingsFactory(pk=1)

    def test_get_success_initial_form_data(self):
        """
        Test successful GET request. Ensures the form is initialized with correct
        TempSalesBooking data and context variables are present.
        """
        test_date = datetime.date.today() + datetime.timedelta(days=7)
        test_time = datetime.time(10, 30)
        temp_booking = self._create_temp_booking_in_session(
            self.client,
            request_viewing=True,
            appointment_date=test_date,
            appointment_time=test_time,
            customer_notes="Test notes for viewing.",
            terms_accepted=True,
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/step2_booking_details.html')
        self.assertIn('form', response.context)
        self.assertIn('temp_booking', response.context)
        self.assertIn('inventory_settings', response.context)
        self.assertIn('min_appointment_date', response.context)
        self.assertIn('max_appointment_date', response.context)
        self.assertIn('blocked_appointment_dates_json', response.context)

        form = response.context['form']
        self.assertTrue(isinstance(form, BookingAppointmentForm))

        # Check initial data on the form
        self.assertEqual(form['request_viewing'].value(), 'yes')
        self.assertEqual(form['appointment_date'].value(), test_date)
        self.assertEqual(form['appointment_time'].value(), test_time)
        self.assertEqual(form['customer_notes'].value(), "Test notes for viewing.")
        self.assertEqual(form['terms_accepted'].value(), True)

        # Check context variables values
        self.assertEqual(response.context['temp_booking'], temp_booking)
        self.assertEqual(response.context['inventory_settings'], self.inventory_settings)
        # Dates are dynamic, just check presence
        self.assertIsNotNone(response.context['min_appointment_date'])
        self.assertIsNotNone(response.context['max_appointment_date'])
        self.assertIsNotNone(response.context['blocked_appointment_dates_json'])
        self.assertTrue(json.loads(response.context['blocked_appointment_dates_json']) is not None)


    # --- POST Request Tests ---

    @mock.patch('django.contrib.messages.success')
    @mock.patch('django.contrib.messages.error')
    def test_post_no_temp_booking_id_in_session(self, mock_error, mock_success):
        """
        Test POST request when 'temp_sales_booking_uuid' is not in session.
        Should redirect with an error message.
        """
        response = self.client.post(self.url, data={}, follow=True)
        self.assertRedirects(response, reverse('core:index'))
        mock_error.assert_called_once_with(mock.ANY, "Your booking session has expired or is invalid. Please start again.")
        mock_success.assert_not_called()

    @mock.patch('django.contrib.messages.success')
    @mock.patch('django.contrib.messages.error')
    def test_post_invalid_temp_booking_id(self, mock_error, mock_success):
        """
        Test POST request with an invalid 'temp_sales_booking_uuid' in session.
        Should redirect with an error message.
        """
        session = self.client.session
        session['temp_sales_booking_uuid'] = 'a2b3c4d5-e6f7-8901-2345-67890abcdef0' # Invalid UUID
        session.save()

        response = self.client.post(self.url, data={'terms_accepted': 'on'}, follow=True) # Send some data to trigger POST logic
        self.assertRedirects(response, reverse('core:index'))
        mock_error.assert_called_once()
        self.assertIn("Your booking session could not be found or is invalid.", str(mock_error.call_args[0][1]))
        mock_success.assert_not_called()

    @mock.patch('django.contrib.messages.success')
    @mock.patch('django.contrib.messages.error')
    def test_post_no_inventory_settings(self, mock_error, mock_success):
        """
        Test POST request when no InventorySettings exist.
        Should redirect to 'core:index' with an error message.
        """
        self._create_temp_booking_in_session(self.client)
        InventorySettings.objects.all().delete() # Delete settings AFTER temp booking is in session

        response = self.client.post(self.url, data={'terms_accepted': 'on'}, follow=True)
        self.assertRedirects(response, reverse('core:index'))
        mock_error.assert_called_once_with(mock.ANY, "Inventory settings are not configured. Please contact support.")
        mock_success.assert_not_called()

        # Recreate settings for other tests
        self.inventory_settings = InventorySettingsFactory(pk=1)

    @mock.patch('inventory.utils.convert_temp_sales_booking.convert_temp_sales_booking')
    @mock.patch('django.contrib.messages.success')
    @mock.patch('django.contrib.messages.error')
    def test_post_valid_data_deposit_required(self, mock_error, mock_success, mock_convert_temp_sales_booking):
        """
        Test valid POST request when deposit_required_for_flow is True.
        Should update TempSalesBooking and redirect to step3_payment.
        """
        # Ensure deposit is required for this flow by setting it on the TempSalesBooking instance
        temp_booking = self._create_temp_booking_in_session(self.client, deposit_required_for_flow=True)

        post_date = datetime.date.today() + datetime.timedelta(days=10)
        post_time = datetime.time(14, 0)
        post_data = {
            'request_viewing': 'yes',
            'appointment_date': post_date.strftime('%Y-%m-%d'),
            'appointment_time': post_time.strftime('%H:%M'),
            'customer_notes': 'Looking forward to the viewing.',
            'terms_accepted': 'on', # Checkbox value
        }

        response = self.client.post(self.url, data=post_data, follow=True)

        # Assert redirection to step3_payment
        self.assertRedirects(response, reverse('inventory:step3_payment'))
        mock_success.assert_called_once_with(mock.ANY, "Booking details saved. Proceed to payment.")
        mock_error.assert_not_called()
        mock_convert_temp_sales_booking.assert_not_called() # Should not be called if deposit required

        # Verify TempSalesBooking is updated
        temp_booking.refresh_from_db() # This is fine here as temp_booking is NOT deleted in this flow
        self.assertTrue(temp_booking.request_viewing)
        self.assertEqual(temp_booking.appointment_date, post_date)
        self.assertEqual(temp_booking.appointment_time, post_time)
        self.assertEqual(temp_booking.customer_notes, 'Looking forward to the viewing.')
        self.assertTrue(temp_booking.terms_accepted)



    @mock.patch('django.contrib.messages.success')
    @mock.patch('django.contrib.messages.error')
    def test_post_invalid_data(self, mock_error, mock_success):
        """
        Test POST request with invalid form data.
        Should re-render the form with errors and an error message.
        """
        temp_booking = self._create_temp_booking_in_session(self.client)

        # Invalid data: terms_accepted is required but not provided
        post_data = {
            'request_viewing': 'yes',
            'appointment_date': (datetime.date.today() + datetime.timedelta(days=1)).strftime('%Y-%m-%d'),
            'appointment_time': datetime.time(11, 0).strftime('%H:%M'),
            'customer_notes': 'Invalid submission test.',
            # 'terms_accepted' is missing
        }
        response = self.client.post(self.url, data=post_data)

        self.assertEqual(response.status_code, 200) # Should re-render the page
        self.assertTemplateUsed(response, 'inventory/step2_booking_details.html')
        mock_error.assert_called_once_with(mock.ANY, "Please correct the errors below.")
        mock_success.assert_not_called()

        # Check if form errors are present in the context
        self.assertIn('form', response.context)
        form = response.context['form']
        self.assertIn('terms_accepted', form.errors)
        # print(form.errors) # Debugging line to see form errors

        # Verify TempSalesBooking is NOT updated on invalid submission
        temp_booking_before_post = temp_booking
        temp_booking.refresh_from_db()
        self.assertEqual(temp_booking.request_viewing, temp_booking_before_post.request_viewing)
        self.assertEqual(temp_booking.appointment_date, temp_booking_before_post.appointment_date)
        self.assertEqual(temp_booking.appointment_time, temp_booking_before_post.appointment_time)


    @mock.patch('django.contrib.messages.success')
    @mock.patch('django.contrib.messages.error')
    def test_post_invalid_date_or_time_format(self, mock_error, mock_success):
        """
        Test POST with invalid date/time format.
        """
        temp_booking = self._create_temp_booking_in_session(self.client)

        post_data = {
            'request_viewing': 'yes',
            'appointment_date': '2023/12/30', # Invalid format
            'appointment_time': '25:00', # Invalid time
            'customer_notes': 'Bad date/time test.',
            'terms_accepted': 'on',
        }
        response = self.client.post(self.url, data=post_data)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertIn('appointment_date', form.errors)
        self.assertIn('appointment_time', form.errors)
        mock_error.assert_called_once_with(mock.ANY, "Please correct the errors below.")
        mock_success.assert_not_called()

    @mock.patch('django.contrib.messages.success')
    @mock.patch('django.contrib.messages.error')
    def test_post_appointment_required_for_viewing(self, mock_error, mock_success):
        """
        Test that appointment_date and appointment_time are required if request_viewing is 'yes'.
        """
        temp_booking = self._create_temp_booking_in_session(self.client)

        post_data = {
            'request_viewing': 'yes', # User requests viewing
            'appointment_date': '', # But no date provided
            'appointment_time': '', # And no time provided
            'customer_notes': 'Viewing requested but no details.',
            'terms_accepted': 'on',
        }
        response = self.client.post(self.url, data=post_data)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertIn('appointment_date', form.errors)
        self.assertIn('appointment_time', form.errors)
        mock_error.assert_called_once_with(mock.ANY, "Please correct the errors below.")
        mock_success.assert_not_called()


