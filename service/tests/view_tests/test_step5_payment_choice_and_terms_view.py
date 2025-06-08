# service/tests/view_tests/test_step5_payment_choice_and_terms_view.py

from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.messages import get_messages
from django.contrib.auth import get_user_model
import datetime
from datetime import time, timedelta
import uuid
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.http import HttpResponse

# Import the view to be tested
from service.views.user_views import Step5PaymentDropoffAndTermsView
from service.views.user_views import Step6PaymentView

# Import models and factories
from service.models import TempServiceBooking, ServiceProfile, CustomerMotorcycle, ServiceType, ServiceSettings
from service.forms.step5_payment_choice_and_terms_form import (
    PaymentOptionForm,
    PAYMENT_OPTION_DEPOSIT,
    PAYMENT_OPTION_FULL_ONLINE,
    PAYMENT_OPTION_INSTORE
)
from ..test_helpers.model_factories import (
    UserFactory,
    ServiceProfileFactory,
    TempServiceBookingFactory,
    CustomerMotorcycleFactory,
    ServiceTypeFactory,
    ServiceSettingsFactory,
)

User = get_user_model()

class Step5PaymentDropoffAndTermsViewTest(TestCase):
    """
    Tests for the Step5PaymentDropoffAndTermsView (dispatch, GET, and POST methods).
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up common data for all tests in this class.
        """
        cls.factory = RequestFactory()
        cls.user_password = 'testpassword123'
        cls.user = UserFactory(password=cls.user_password) # For authenticated tests
        
        # Ensure ServiceSettings exists and has expected values for dynamic form choices
        cls.service_settings = ServiceSettingsFactory(
            enable_online_full_payment=True,
            enable_online_deposit=True,
            enable_instore_full_payment=True,
            enable_deposit=True, # Important for deposit option visibility
            deposit_calc_method='FLAT_FEE',
            deposit_flat_fee_amount=Decimal('50.00'),
            currency_symbol='$',
            max_advance_dropoff_days=10, # For testing date validations
            latest_same_day_dropoff_time=time(12, 0), # 12:00 PM cutoff
            drop_off_start_time=time(9, 0),
            drop_off_end_time=time(17, 0),
        )
        cls.service_type = ServiceTypeFactory(base_price=Decimal('250.00'))
        cls.base_url = reverse('service:service_book_step5')

    def setUp(self):
        """
        Set up for each test method.
        Ensure a clean state for temporary bookings, etc.
        """
        TempServiceBooking.objects.all().delete()
        ServiceProfile.objects.all().delete()
        CustomerMotorcycle.objects.all().delete()

        # Create necessary linked objects for temp_booking to be valid for step 5
        self.customer_motorcycle = CustomerMotorcycleFactory(
            brand="Honda", model="CBR", year=2020, rego="TESTMC"
        )
        self.service_profile = ServiceProfileFactory(user=self.user, email="test@example.com")

        # Create a valid temporary service booking
        self.temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_date=datetime.date.today() + datetime.timedelta(days=10), # Service date in the future
            customer_motorcycle=self.customer_motorcycle, # Linked from step 3
            service_profile=self.service_profile, # Linked from step 4
            dropoff_date=None, # Will be set in this step
            dropoff_time=None, # Will be set in this step
            payment_option=None, # Will be set in this step
            calculated_deposit_amount=Decimal('50.00') # Example deposit
        )

        # Set the UUID in the client's session
        session = self.client.session
        session['temp_service_booking_uuid'] = str(self.temp_booking.session_uuid)
        session.save()
        
        # Default valid data for POST requests (can be overridden in specific tests)
        self.valid_post_data = {
            'dropoff_date': (datetime.date.today() + datetime.timedelta(days=7)).strftime('%Y-%m-%d'),
            'dropoff_time': '10:30',
            'payment_option': PAYMENT_OPTION_FULL_ONLINE,
            'service_terms_accepted': True,
        }

    # --- Dispatch Method Tests ---

    def test_dispatch_no_temp_booking_uuid_in_session_redirects_to_service_home(self):
        """
        Tests that dispatch redirects to service:service if no temp_service_booking_uuid is in session.
        """
        self.client.logout() # Ensure clean session
        session = self.client.session
        if 'temp_service_booking_uuid' in session:
            del session['temp_service_booking_uuid']
        session.save()

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('service:service'), fetch_redirect_response=False)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Your booking session has expired." in str(m) for m in messages))

    def test_dispatch_invalid_temp_booking_uuid_redirects_to_service_home(self):
        """
        Tests that dispatch redirects to service:service if an invalid temp_service_booking_uuid is in session.
        """
        session = self.client.session
        session['temp_service_booking_uuid'] = str(uuid.uuid4()) # Non-existent UUID
        session.save()

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('service:service'), fetch_redirect_response=False)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Your booking session could not be found." in str(m) for m in messages))

    def test_dispatch_no_service_profile_redirects_to_step4(self):
        """
        Tests that dispatch redirects to step4 if no service profile is linked to temp_booking.
        """
        self.temp_booking.service_profile = None
        self.temp_booking.save()
        
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('service:service_book_step4'), fetch_redirect_response=False)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Please complete your personal details first (Step 4)." in str(m) for m in messages))

    def test_dispatch_no_service_settings_redirects_to_service_home(self):
        """
        Tests that dispatch redirects to service:service if ServiceSettings are not configured.
        """
        ServiceSettings.objects.all().delete() # Remove existing settings
        
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('service:service'), fetch_redirect_response=False)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Service settings are not configured." in str(m) for m in messages))

    def test_dispatch_valid_temp_booking_proceeds(self):
        """
        Tests that dispatch allows the request to proceed with a valid temporary booking.
        """
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200) # Should render the form
        self.assertTemplateUsed(response, 'service/step5_payment_dropoff_and_terms.html')

    # --- GET Method Tests ---

    def test_get_renders_form_with_initial_data_from_temp_booking(self):
        """
        Tests that GET request renders the form with initial data if present in temp_booking.
        """
        # Set some initial data on temp_booking
        self.temp_booking.dropoff_date = datetime.date.today() + datetime.timedelta(days=5)
        self.temp_booking.dropoff_time = time(11, 0)
        self.temp_booking.payment_option = PAYMENT_OPTION_DEPOSIT
        self.temp_booking.save()

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertIsInstance(form, PaymentOptionForm)
        self.assertEqual(form.initial['dropoff_date'], self.temp_booking.dropoff_date)
        self.assertEqual(form.initial['dropoff_time'], self.temp_booking.dropoff_time)
        self.assertEqual(form.initial['payment_option'], self.temp_booking.payment_option)

    def test_get_context_data_same_day_dropoff_only_when_max_advance_is_zero(self):
        """
        Tests that 'is_same_day_dropoff_only' is True when max_advance_dropoff_days is 0.
        """
        self.service_settings.max_advance_dropoff_days = 0
        self.service_settings.save()

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_same_day_dropoff_only'])
        # Also check initial dropoff_date is forced to service_date
        form = response.context['form']
        self.assertEqual(form.initial['dropoff_date'], self.temp_booking.service_date)


    # --- POST Method Tests ---

    def test_post_valid_data_updates_temp_booking_and_redirects_to_step6(self):
        """
        Tests that valid POST data updates the temp_booking and redirects to step 6.
        """
        initial_dropoff_date = self.temp_booking.dropoff_date
        initial_dropoff_time = self.temp_booking.dropoff_time
        initial_payment_option = self.temp_booking.payment_option

        response = self.client.post(self.base_url, self.valid_post_data)

        self.assertEqual(response.status_code, 302)
        # It redirects to step6, which then renders a page (200) or redirects further (302).
        # We need to explicitly tell assertRedirects to NOT follow the redirect to check the first hop.
        self.assertRedirects(response, reverse('service:service_book_step6'), fetch_redirect_response=False)

        self.temp_booking.refresh_from_db()
        self.assertEqual(self.temp_booking.dropoff_date, datetime.date.fromisoformat(self.valid_post_data['dropoff_date']))
        self.assertEqual(self.temp_booking.dropoff_time, datetime.time.fromisoformat(self.valid_post_data['dropoff_time']))
        self.assertEqual(self.temp_booking.payment_option, self.valid_post_data['payment_option'])
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Drop-off and payment details have been saved successfully." in str(m) for m in messages))


    def test_post_invalid_data_rerenders_form_with_errors(self):
        """
        Tests that invalid POST data re-renders the form with errors.
        """
        invalid_data = self.valid_post_data.copy()
        invalid_data['dropoff_date'] = 'invalid-date' # Invalid date format
        invalid_data['service_terms_accepted'] = False # Not accepted

        response = self.client.post(self.base_url, invalid_data)

        self.assertEqual(response.status_code, 200) # Should re-render
        self.assertTemplateUsed(response, 'service/step5_payment_dropoff_and_terms.html')
        self.assertIn('form', response.context)
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertIn('dropoff_date', form.errors)
        self.assertIn('service_terms_accepted', form.errors) # Error for not accepting terms

        self.temp_booking.refresh_from_db() # Should not have saved invalid data
        self.assertIsNone(self.temp_booking.dropoff_date)
        self.assertIsNone(self.temp_booking.dropoff_time)
        self.assertIsNone(self.temp_booking.payment_option)
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Please correct the errors highlighted below." in str(m) for m in messages))

    def test_post_dropoff_date_after_service_date_is_invalid(self):
        """
        Tests that drop-off date cannot be after the service date.
        """
        invalid_data = self.valid_post_data.copy()
        # Set drop-off date one day AFTER the service_date
        invalid_data['dropoff_date'] = (self.temp_booking.service_date + datetime.timedelta(days=1)).strftime('%Y-%m-%d')

        response = self.client.post(self.base_url, invalid_data)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertIn('dropoff_date', form.errors)
        self.assertIn("Drop-off date cannot be after the service date.", form.errors['dropoff_date'][0])

    def test_post_dropoff_date_too_far_in_advance_is_invalid(self):
        """
        Tests that drop-off date cannot be too far in advance of the service date.
        """
        # max_advance_dropoff_days is 10 in setUpTestData
        invalid_data = self.valid_post_data.copy()
        # Set drop-off date 11 days before service date
        invalid_data['dropoff_date'] = (self.temp_booking.service_date - datetime.timedelta(days=11)).strftime('%Y-%m-%d')

        response = self.client.post(self.base_url, invalid_data)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertIn('dropoff_date', form.errors)
        self.assertIn(f"Drop-off cannot be scheduled more than {self.service_settings.max_advance_dropoff_days} days in advance of the service.", form.errors['dropoff_date'][0])

    def test_post_same_day_dropoff_time_in_past_is_invalid(self):
        """
        Tests that for same-day drop-off, time cannot be in the past.
        """
        # Set service_date to today, and max_advance_dropoff_days to allow same-day
        self.temp_booking.service_date = datetime.date.today()
        self.temp_booking.save()
        self.service_settings.max_advance_dropoff_days = 0 # Force same-day drop-off
        self.service_settings.save()

        # Mock timezone.localtime(timezone.now()).time() to a known future time
        # so we can test selecting a time *before* it.
        with self.settings(USE_TZ=True, TIME_ZONE='Australia/Perth'):
            with patch('django.utils.timezone.localtime') as mock_localtime:
                # Configure the mock to return a datetime object with the desired time
                mock_localtime.return_value = datetime.datetime.combine(
                    datetime.date.today(),
                    time(11, 0), # Mock current time to 11:00 AM
                    tzinfo=datetime.timezone.utc # Simplified for mock, use actual tz if needed
                ).astimezone(datetime.timezone.utc) # Convert to UTC-aware datetime for comparison consistency

                invalid_data = self.valid_post_data.copy()
                invalid_data['dropoff_date'] = datetime.date.today().strftime('%Y-%m-%d')
                invalid_data['dropoff_time'] = '10:00' # Before mocked current time of 11:00 AM

                response = self.client.post(self.base_url, invalid_data)
                self.assertEqual(response.status_code, 200)
                form = response.context['form']
                self.assertFalse(form.is_valid())
                self.assertIn('dropoff_time', form.errors)
                self.assertIn("You cannot select a drop-off time that has already passed today.", form.errors['dropoff_time'][0])

    # Test for payment option choices being populated correctly (implicitly covered by form rendering)
    # but could be explicit if needed.
    def test_payment_option_choices_are_correctly_populated(self):
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        
        expected_choices = [
            (PAYMENT_OPTION_DEPOSIT, f"Pay Deposit Online (${self.service_settings.deposit_flat_fee_amount:.2f})"),
            (PAYMENT_OPTION_FULL_ONLINE, "Pay Full Amount Online Now"),
            (PAYMENT_OPTION_INSTORE, "Pay In-Store on Drop-off"),
        ]
        self.assertEqual(list(form.fields['payment_option'].choices), expected_choices)


    @patch('service.views.user_views.Step6PaymentView.dispatch')
    def test_post_payment_option_deposit_online(self, mock_step6_dispatch):
        """
        Tests that submitting with deposit_online option works and correctly triggers redirect to Step 6.
        We mock Step6PaymentView.dispatch to prevent it from performing its own redirects
        during this test, ensuring we only assert the redirect from Step 5.
        """
        # Simplest way to mock a successful response from the next view's dispatch
        mock_step6_dispatch.return_value = HttpResponse(status=200) 

        valid_data = self.valid_post_data.copy()
        valid_data['payment_option'] = PAYMENT_OPTION_DEPOSIT
        response = self.client.post(self.base_url, valid_data)
        
        # Assert that Step5 redirected to Step6 (302 status)
        self.assertEqual(response.status_code, 302)
        # assertRedirects follows redirects. If mock_step6_dispatch returns 200, it means the redirect was "successful".
        self.assertRedirects(response, reverse('service:service_book_step6')) 
        
        self.temp_booking.refresh_from_db()
        self.assertEqual(self.temp_booking.payment_option, PAYMENT_OPTION_DEPOSIT)
        mock_step6_dispatch.assert_called_once()
