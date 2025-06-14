# # inventory/tests/test_views/test_step2_booking_details_view.py

# import datetime
# from django.test import TestCase, Client
# from django.urls import reverse
# from django.contrib.messages import get_messages
# from unittest import mock
# import json # For checking JSON output

# from inventory.models import TempSalesBooking, SalesProfile, InventorySettings, SalesBooking
# from ...test_helpers.model_factories import (
#     TempSalesBookingFactory,
#     InventorySettingsFactory,
#     MotorcycleFactory,
#     SalesProfileFactory,
# )

# class Step2BookingDetailsViewTest(TestCase):
#     """
#     Tests for the Step2BookingDetailsView.
#     """

#     @classmethod
#     def setUpTestData(cls):
#         """
#         Set up common data for all tests in this class.
#         """
#         cls.client = Client()
#         cls.url = reverse('inventory:booking_details_and_appointment')

#         # Ensure a singleton InventorySettings instance exists
#         cls.inventory_settings = InventorySettingsFactory(
#             sales_appointment_start_time=datetime.time(9, 0),
#             sales_appointment_end_time=datetime.time(17, 0),
#             sales_appointment_spacing_mins=30,
#             min_advance_booking_hours=0, # Set to 0 for easier date testing
#             max_advance_booking_days=90,
#             deposit_lifespan_days=5,
#             enable_viewing_for_enquiry=True, # Default to True for most tests
#         )

#         # Create a dummy motorcycle and sales profile
#         cls.motorcycle = MotorcycleFactory()
#         cls.sales_profile = SalesProfileFactory()

#     def _create_temp_booking_in_session(self, client, deposit_required=False, sales_profile=None):
#         """Helper to create a TempSalesBooking and set its ID in the session."""
#         temp_booking = TempSalesBookingFactory(
#             motorcycle=self.motorcycle,
#             sales_profile=sales_profile if sales_profile else self.sales_profile,
#             deposit_required_for_flow=deposit_required,
#             booking_status='pending_details' # Initial status for Step 2
#         )
#         session = client.session
#         session['current_temp_booking_id'] = temp_booking.pk
#         session.save()
#         return temp_booking

#     # --- GET Request Tests ---

#     def test_get_no_temp_booking_id_in_session(self):
#         """
#         Test GET request when 'current_temp_booking_id' is not in session.
#         Should redirect to core:index with an error message.
#         """
#         response = self.client.get(self.url, follow=True)
#         self.assertRedirects(response, reverse('core:index'))
#         messages = list(get_messages(response.wsgi_request))
#         self.assertEqual(len(messages), 1)
#         self.assertEqual(str(messages[0]), "Your booking session has expired or is invalid. Please start again.")

#     def test_get_invalid_temp_booking_id(self):
#         """
#         Test GET request with an invalid 'current_temp_booking_id' in session.
#         Should return a 404.
#         """
#         session = self.client.session
#         session['current_temp_booking_id'] = 99999 # Non-existent ID
#         session.save()

#         response = self.client.get(self.url)
#         self.assertEqual(response.status_code, 404)

#     def test_get_no_inventory_settings(self):
#         """
#         Test GET request when no InventorySettings exist.
#         Should redirect to core:index with an error message.
#         """
#         # Delete existing settings
#         InventorySettings.objects.all().delete()
#         self.assertFalse(InventorySettings.objects.exists()) # Verify deletion

#         self._create_temp_booking_in_session(self.client) # Need a valid temp booking ID

#         response = self.client.get(self.url, follow=True)
#         self.assertRedirects(response, reverse('core:index'))
#         messages = list(get_messages(response.wsgi_request))
#         self.assertEqual(len(messages), 1)
#         self.assertEqual(str(messages[0]), "Inventory settings are not configured. Please contact support.")

#         # Recreate settings for other tests
#         self.inventory_settings = InventorySettingsFactory(pk=1)


#     def test_get_success_deposit_flow(self):
#         """
#         Test successful GET request for a deposit-required flow.
#         request_viewing should be forced to 'yes', appointment fields visible.
#         """
#         temp_booking = self._create_temp_booking_in_session(self.client, deposit_required=True)

#         response = self.client.get(self.url)
#         self.assertEqual(response.status_code, 200)
#         self.assertTemplateUsed(response, 'inventory/step2_booking_details.html')
#         self.assertIn('form', response.context)
#         self.assertEqual(response.context['temp_booking'], temp_booking)
#         self.assertIn('min_appointment_date', response.context)
#         self.assertIn('max_appointment_date', response.context)
#         self.assertIn('blocked_appointment_dates_json', response.context)

#         form = response.context['form']
#         # For deposit flow, request_viewing should be hidden and forced to 'yes'
#         self.assertIsInstance(form.fields['request_viewing'].widget, mock.ANY) # Check if it's HiddenInput
#         self.assertTrue(form.initial['request_viewing'] == 'yes' or form.initial['request_viewing'] is True) # Check initial value

#         # Ensure appointment date/time fields are required
#         self.assertTrue(form.fields['appointment_date'].required)
#         self.assertTrue(form.fields['appointment_time'].required)


#     def test_get_success_depositless_viewing_enabled(self):
#         """
#         Test successful GET request for depositless flow where viewing is enabled.
#         request_viewing should be visible.
#         """
#         self.inventory_settings.enable_viewing_for_enquiry = True
#         self.inventory_settings.save()
#         temp_booking = self._create_temp_booking_in_session(self.client, deposit_required=False)

#         response = self.client.get(self.url)
#         self.assertEqual(response.status_code, 200)
#         form = response.context['form']
#         # For depositless viewing enabled, request_viewing should be a RadioSelect
#         self.assertIsInstance(form.fields['request_viewing'].widget, forms.RadioSelect)
#         self.assertFalse(form.fields['appointment_date'].required) # Not required by default without 'yes' selected
#         self.assertFalse(form.fields['appointment_time'].required)

#     def test_get_success_depositless_viewing_disabled(self):
#         """
#         Test successful GET request for depositless flow where viewing is disabled.
#         request_viewing should be forced to 'no', appointment fields hidden.
#         """
#         self.inventory_settings.enable_viewing_for_enquiry = False
#         self.inventory_settings.save()
#         temp_booking = self._create_temp_booking_in_session(self.client, deposit_required=False)

#         response = self.client.get(self.url)
#         self.assertEqual(response.status_code, 200)
#         form = response.context['form']
#         # For depositless viewing disabled, request_viewing should be hidden and forced to 'no'
#         self.assertIsInstance(form.fields['request_viewing'].widget, mock.ANY) # Check if it's HiddenInput
#         self.assertTrue(form.initial['request_viewing'] == 'no' or form.initial['request_viewing'] is False) # Check initial value

#         # Ensure appointment date/time fields are not required and hidden
#         self.assertFalse(form.fields['appointment_date'].required)
#         self.assertFalse(form.fields['appointment_time'].required)
#         self.assertIsInstance(form.fields['appointment_date'].widget, mock.ANY) # Check HiddenInput
#         self.assertIsInstance(form.fields['appointment_time'].widget, mock.ANY) # Check HiddenInput


#     # --- POST Request Tests ---

#     @mock.patch('django.contrib.messages.success')
#     @mock.patch('django.contrib.messages.error')
#     def test_post_no_temp_booking_id_in_session(self, mock_error, mock_success):
#         """
#         Test POST request when 'current_temp_booking_id' is not in session.
#         Should redirect to core:index with an error message.
#         """
#         response = self.client.post(self.url, data={}, follow=True)
#         self.assertRedirects(response, reverse('core:index'))
#         mock_error.assert_called_once_with(mock.ANY, "Your booking session has expired or is invalid. Please start again.")
#         mock_success.assert_not_called()

#     @mock.patch('django.contrib.messages.success')
#     @mock.patch('django.contrib.messages.error')
#     def test_post_invalid_temp_booking_id(self, mock_error, mock_success):
#         """
#         Test POST request with an invalid 'current_temp_booking_id' in session.
#         Should return a 404.
#         """
#         session = self.client.session
#         session['current_temp_booking_id'] = 99999 # Non-existent ID
#         session.save()

#         response = self.client.post(self.url, data={'terms_accepted': 'on'})
#         self.assertEqual(response.status_code, 404)
#         mock_error.assert_not_called()
#         mock_success.assert_not_called()

#     @mock.patch('django.contrib.messages.success')
#     @mock.patch('django.contrib.messages.error')
#     def test_post_no_inventory_settings(self, mock_error, mock_success):
#         """
#         Test POST request when no InventorySettings exist.
#         Should redirect to core:index with an error message.
#         """
#         InventorySettings.objects.all().delete()
#         self._create_temp_booking_in_session(self.client) # Need a valid temp booking ID

#         response = self.client.post(self.url, data={'terms_accepted': 'on'}, follow=True)
#         self.assertRedirects(response, reverse('core:index'))
#         mock_error.assert_called_once_with(mock.ANY, "Inventory settings are not configured. Please contact support.")
#         mock_success.assert_not_called()

#         # Recreate settings for other tests
#         self.inventory_settings = InventorySettingsFactory(pk=1)


#     @mock.patch('django.contrib.messages.success')
#     @mock.patch('django.contrib.messages.error')
#     def test_post_valid_data_deposit_flow(self, mock_error, mock_success):
#         """
#         Test successful POST for deposit flow (requires appointment).
#         Should redirect to payment page.
#         """
#         temp_booking = self._create_temp_booking_in_session(self.client, deposit_required=True)
#         today = datetime.date.today() + datetime.timedelta(days=1) # A valid date

#         post_data = {
#             'request_viewing': 'yes', # Hidden input for deposit flow
#             'appointment_date': today.strftime('%Y-%m-%d'),
#             'appointment_time': '10:00',
#             'customer_notes': 'Looking forward to it!',
#             'terms_accepted': 'on', # Checkbox value for True
#         }
#         response = self.client.post(self.url, data=post_data, follow=True)

#         self.assertRedirects(response, reverse('inventory:payment_page'))
#         mock_success.assert_called_once_with(mock.ANY, "Booking details saved. Proceed to payment.")
#         mock_error.assert_not_called()

#         # Verify TempSalesBooking is updated
#         temp_booking.refresh_from_db()
#         self.assertEqual(temp_booking.appointment_date, today)
#         self.assertEqual(temp_booking.appointment_time, datetime.time(10, 0))
#         self.assertEqual(temp_booking.customer_notes, 'Looking forward to it!')
#         self.assertTrue(temp_booking.request_viewing)
#         self.assertTrue(temp_booking.terms_accepted)


#     @mock.patch('django.contrib.messages.success')
#     @mock.patch('django.contrib.messages.error')
#     @mock.patch('inventory.utils.convert_temp_sales_booking.convert_temp_sales_booking')
#     def test_post_valid_data_depositless_viewing_yes(self, mock_convert, mock_error, mock_success):
#         """
#         Test successful POST for depositless flow with viewing requested.
#         Should convert to SalesBooking and redirect to confirmation.
#         """
#         self.inventory_settings.enable_viewing_for_enquiry = True
#         self.inventory_settings.save()
#         temp_booking = self._create_temp_booking_in_session(self.client, deposit_required=False)
#         today = datetime.date.today() + datetime.timedelta(days=1) # A valid date

#         # Mock the convert_temp_sales_booking utility
#         mock_converted_booking = SalesBooking(sales_booking_reference='MOCKEDREF123')
#         mock_convert.return_value = mock_converted_booking

#         post_data = {
#             'request_viewing': 'yes',
#             'appointment_date': today.strftime('%Y-%m-%d'),
#             'appointment_time': '11:00',
#             'customer_notes': 'Just an enquiry for viewing',
#             'terms_accepted': 'on',
#         }
#         response = self.client.post(self.url, data=post_data, follow=True)

#         self.assertRedirects(response, reverse('inventory:confirmation_page'))
#         mock_success.assert_called_once_with(mock.ANY, "Your enquiry has been submitted. We will get back to you shortly!")
#         mock_error.assert_not_called()

#         # Verify TempSalesBooking is updated
#         temp_booking.refresh_from_db()
#         self.assertEqual(temp_booking.appointment_date, today)
#         self.assertEqual(temp_booking.appointment_time, datetime.time(11, 0))
#         self.assertEqual(temp_booking.customer_notes, 'Just an enquiry for viewing')
#         self.assertTrue(temp_booking.request_viewing)
#         self.assertTrue(temp_booking.terms_accepted)

#         # Verify convert_temp_sales_booking was called
#         mock_convert.assert_called_once_with(
#             temp_booking=temp_booking,
#             booking_payment_status='unpaid',
#             amount_paid_on_booking=Decimal('0.00'),
#             stripe_payment_intent_id=None,
#             payment_obj=None,
#         )
#         self.assertIn('current_sales_booking_reference', self.client.session)
#         self.assertEqual(self.client.session['current_sales_booking_reference'], 'MOCKEDREF123')


#     @mock.patch('django.contrib.messages.success')
#     @mock.patch('django.contrib.messages.error')
#     @mock.patch('inventory.utils.convert_temp_sales_booking.convert_temp_sales_booking')
#     def test_post_valid_data_depositless_viewing_no(self, mock_convert, mock_error, mock_success):
#         """
#         Test successful POST for depositless flow with NO viewing requested.
#         Should convert to SalesBooking (without appointment details) and redirect to confirmation.
#         """
#         self.inventory_settings.enable_viewing_for_enquiry = True # Viewing is generally enabled
#         self.inventory_settings.save()
#         temp_booking = self._create_temp_booking_in_session(self.client, deposit_required=False)

#         # Mock the convert_temp_sales_booking utility
#         mock_converted_booking = SalesBooking(sales_booking_reference='MOCKEDREF456')
#         mock_convert.return_value = mock_converted_booking

#         post_data = {
#             'request_viewing': 'no', # User explicitly selects 'no' viewing
#             'customer_notes': 'General enquiry only',
#             'terms_accepted': 'on',
#             # Appointment date/time should be optional and thus can be omitted
#         }
#         response = self.client.post(self.url, data=post_data, follow=True)

#         self.assertRedirects(response, reverse('inventory:confirmation_page'))
#         mock_success.assert_called_once_with(mock.ANY, "Your enquiry has been submitted. We will get back to you shortly!")
#         mock_error.assert_not_called()

#         # Verify TempSalesBooking is updated (appointment fields should be cleared)
#         temp_booking.refresh_from_db()
#         self.assertIsNone(temp_booking.appointment_date)
#         self.assertIsNone(temp_booking.appointment_time)
#         self.assertEqual(temp_booking.customer_notes, 'General enquiry only')
#         self.assertFalse(temp_booking.request_viewing)
#         self.assertTrue(temp_booking.terms_accepted)

#         # Verify convert_temp_sales_booking was called
#         mock_convert.assert_called_once_with(
#             temp_booking=temp_booking,
#             booking_payment_status='unpaid',
#             amount_paid_on_booking=Decimal('0.00'),
#             stripe_payment_intent_id=None,
#             payment_obj=None,
#         )
#         self.assertIn('current_sales_booking_reference', self.client.session)
#         self.assertEqual(self.client.session['current_sales_booking_reference'], 'MOCKEDREF456')

#     @mock.patch('django.contrib.messages.success')
#     @mock.patch('django.contrib.messages.error')
#     def test_post_invalid_data_missing_appointment_details_when_required(self, mock_error, mock_success):
#         """
#         Test POST request with invalid form data (missing appointment date/time
#         when request_viewing is 'yes').
#         """
#         self.inventory_settings.enable_viewing_for_enquiry = True
#         self.inventory_settings.save()
#         temp_booking = self._create_temp_booking_in_session(self.client, deposit_required=False)

#         post_data = {
#             'request_viewing': 'yes', # Requesting viewing, so date/time are required
#             # 'appointment_date': '', # Missing
#             # 'appointment_time': '', # Missing
#             'customer_notes': 'Forgot to add date',
#             'terms_accepted': 'on',
#         }
#         response = self.client.post(self.url, data=post_data)

#         self.assertEqual(response.status_code, 200) # Should re-render
#         self.assertTemplateUsed(response, 'inventory/step2_booking_details.html')
#         mock_error.assert_called_once_with(mock.ANY, "Please correct the errors below.")
#         mock_success.assert_not_called()

#         form = response.context['form']
#         self.assertIn('appointment_date', form.errors)
#         self.assertIn('appointment_time', form.errors)
#         self.assertIn('min_appointment_date', response.context) # Check date info still passed
#         self.assertIn('max_appointment_date', response.context)
#         self.assertIn('blocked_appointment_dates_json', response.context)

#     @mock.patch('django.contrib.messages.success')
#     @mock.patch('django.contrib.messages.error')
#     def test_post_invalid_data_terms_not_accepted(self, mock_error, mock_success):
#         """
#         Test POST request with invalid form data (terms not accepted).
#         """
#         temp_booking = self._create_temp_booking_in_session(self.client, deposit_required=False)
#         today = datetime.date.today() + datetime.timedelta(days=1)

#         post_data = {
#             'request_viewing': 'yes',
#             'appointment_date': today.strftime('%Y-%m-%d'),
#             'appointment_time': '10:00',
#             'customer_notes': 'Valid data, but no terms',
#             'terms_accepted': '', # Missing or unchecked
#         }
#         response = self.client.post(self.url, data=post_data)

#         self.assertEqual(response.status_code, 200) # Should re-render
#         self.assertTemplateUsed(response, 'inventory/step2_booking_details.html')
#         mock_error.assert_called_once_with(mock.ANY, "Please correct the errors below.")
#         mock_success.assert_not_called()

#         form = response.context['form']
#         self.assertIn('terms_accepted', form.errors)

