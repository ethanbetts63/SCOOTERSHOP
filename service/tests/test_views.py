# service/tests/test_booking_views.py

from django.test import TestCase, Client
from django.urls import reverse, NoReverseMatch # Import NoReverseMatch
from unittest.mock import patch, MagicMock
import datetime
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages

# Import models and forms needed for testing
from service.models import ServiceType, CustomerMotorcycle, ServiceBooking
# Assuming forms are in service.forms
from service.forms import ServiceDetailsForm, CustomerMotorcycleForm, ServiceBookingUserForm, ExistingCustomerMotorcycleForm
# Assuming SiteSettings is in dashboard.models
from dashboard.models import SiteSettings

User = get_user_model()

# Define the session key used in the view
SERVICE_BOOKING_SESSION_KEY = 'service_booking_data'

# Use patch to mock SiteSettings.get_settings for consistent testing
@patch('service.views.booking.SiteSettings.get_settings')
class BookingViewsTestCase(TestCase):

    def setUp(self):
        # Create a test client
        self.client = Client()

        # Create a test user
        self.user = User.objects.create_user(username='testuser', password='password', email='test@example.com')

        # Create a dummy ServiceType
        self.service_type = ServiceType.objects.create(
            name='Standard Service',
            description='A standard motorcycle service.',
            estimated_duration=datetime.timedelta(hours=2),
            base_price=150.00,
            is_active=True
        )

        # URLs using the service namespace
        self.service_start_url = reverse('service:service_start')
        self.service_step1_url = reverse('service:service_step1')
        self.service_step2_auth_url = reverse('service:service_step2_authenticated')
        self.service_step2_anon_url = reverse('service:service_step2_anonymous')

        # Fix for NoReverseMatch: Assuming your login URL is named 'login'
        # within the 'users' namespace. If different, adjust accordingly.
        try:
            self.login_url = reverse('users:login') # Corrected based on user feedback
        except NoReverseMatch:
             print("Warning: 'users:login' URL not found. Check your project's urls.py.")
             raise # Re-raise the exception if the expected login URL is truly missing.

        try:
            self.index_url = reverse('core:index') # Corrected based on likely namespace
        except NoReverseMatch:
            print("Warning: 'core:index' URL not found. Check your project's urls.py.")
            raise # Re-raise the exception if the expected index URL is truly missing.


    # --- Tests for booking_start view ---

    def test_booking_start_redirects_to_step1_when_enabled(self, mock_get_settings):
        """
        Test that booking_start redirects to service_step1 when booking is enabled.
        """
        # Configure mock settings to enable booking
        mock_settings = MagicMock(spec=SiteSettings)
        mock_settings.enable_service_booking = True
        mock_get_settings.return_value = mock_settings

        # Simulate a GET request to booking_start
        response = self.client.get(self.service_start_url)

        # Check that the response is a redirect to service_step1
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.service_step1_url)

        # Check that the session key is cleared
        self.assertNotIn(SERVICE_BOOKING_SESSION_KEY, self.client.session)

    def test_booking_start_redirects_to_index_when_disabled(self, mock_get_settings):
        """
        Test that booking_start redirects to index and shows a message when booking is disabled.
        """
        # Configure mock settings to disable booking
        mock_settings = MagicMock(spec=SiteSettings)
        mock_settings.enable_service_booking = False
        mock_get_settings.return_value = mock_settings

        # Simulate a GET request to booking_start
        response = self.client.get(self.service_start_url)

        # Check that the response is a redirect to the core index view
        self.assertEqual(response.status_code, 302)
        # Assert redirect to the determined index_url
        self.assertRedirects(response, self.index_url)

        # Check for the error message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Service booking is currently disabled.")
        self.assertEqual(messages[0].level, messages[0].ERROR)

        # Check that the session key is cleared (should happen regardless of enable status)
        self.assertNotIn(SERVICE_BOOKING_SESSION_KEY, self.client.session)

    def test_booking_start_clears_session(self, mock_get_settings):
        """
        Test that booking_start always clears the service booking session key.
        """
        # Configure mock settings to enable booking
        mock_settings = MagicMock(spec=SiteSettings)
        mock_settings.enable_service_booking = True
        mock_get_settings.return_value = mock_settings

        # Put some dummy data in the session
        session = self.client.session
        session[SERVICE_BOOKING_SESSION_KEY] = {'dummy_data': 'test'}
        session.save()

        # Simulate a GET request to booking_start
        response = self.client.get(self.service_start_url)

        # Check that the session key is cleared after the request
        self.assertNotIn(SERVICE_BOOKING_SESSION_KEY, self.client.session)

    # --- Tests for booking_step1 view ---

    def test_booking_step1_get_authenticated(self, mock_get_settings):
        """
        Test GET request to booking_step1 for an authenticated user.
        Should render the service_details.html template with the correct context.
        """
        # Configure mock settings to enable booking and allow anonymous
        mock_settings = MagicMock(spec=SiteSettings)
        mock_settings.enable_service_booking = True
        mock_settings.allow_anonymous_bookings = True # Doesn't matter for authenticated user, but good practice
        mock_get_settings.return_value = mock_settings

        # Log in the test user
        self.client.login(username='testuser', password='password')

        # Simulate a GET request to booking_step1
        response = self.client.get(self.service_step1_url)

        # Check that the response is successful (status code 200)
        self.assertEqual(response.status_code, 200)

        # Check that the correct template is used
        self.assertTemplateUsed(response, 'service/service_details.html')

        # Check that the context contains the expected variables
        self.assertIn('form', response.context)
        self.assertIsInstance(response.context['form'], ServiceDetailsForm)
        self.assertEqual(response.context['step'], 1)
        self.assertEqual(response.context['total_steps'], 3)
        self.assertTrue(response.context['is_authenticated'])
        self.assertTrue(response.context['allow_anonymous_bookings']) # Should reflect settings

        # Check that the form is not pre-filled initially (no session data)
        self.assertFalse(response.context['form'].initial)

    def test_booking_step1_get_anonymous_allowed(self, mock_get_settings):
        """
        Test GET request to booking_step1 for an anonymous user when anonymous bookings are allowed.
        Should render the service_details.html template with the correct context.
        """
        # Configure mock settings to enable booking and allow anonymous
        mock_settings = MagicMock(spec=SiteSettings)
        mock_settings.enable_service_booking = True
        mock_settings.allow_anonymous_bookings = True
        mock_get_settings.return_value = mock_settings

        # Simulate a GET request as an anonymous user
        response = self.client.get(self.service_step1_url)

        # Check that the response is successful (status code 200)
        self.assertEqual(response.status_code, 200)

        # Check that the correct template is used
        self.assertTemplateUsed(response, 'service/service_details.html')

        # Check that the context contains the expected variables
        self.assertIn('form', response.context)
        self.assertIsInstance(response.context['form'], ServiceDetailsForm)
        self.assertEqual(response.context['step'], 1)
        self.assertEqual(response.context['total_steps'], 3)
        self.assertFalse(response.context['is_authenticated'])
        self.assertTrue(response.context['allow_anonymous_bookings']) # Should reflect settings

        # Check that the form is not pre-filled initially (no session data)
        self.assertFalse(response.context['form'].initial)

    def test_booking_step1_get_anonymous_not_allowed(self, mock_get_settings):
        """
        Test GET request to booking_step1 for an anonymous user when anonymous bookings are NOT allowed.
        Should redirect to the login page.
        """
        # Configure mock settings to enable booking but NOT allow anonymous
        mock_settings = MagicMock(spec=SiteSettings)
        mock_settings.enable_service_booking = True
        mock_settings.allow_anonymous_bookings = False
        mock_get_settings.return_value = mock_settings

        # Simulate a GET request as an anonymous user
        response = self.client.get(self.service_step1_url)

        # Check that the response is a redirect to the login page
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.login_url)

        # Check for the info message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Please log in or register to book a service.")
        self.assertEqual(messages[0].level, messages[0].INFO)


    def test_booking_step1_get_disabled(self, mock_get_settings):
        """
        Test GET request to booking_step1 when service booking is disabled.
        Should redirect to the index page and show an error message.
        """
        # Configure mock settings to disable booking
        mock_settings = MagicMock(spec=SiteSettings)
        mock_settings.enable_service_booking = False
        mock_get_settings.return_value = mock_settings

        # Simulate a GET request
        response = self.client.get(self.service_step1_url)

        # Check that the response is a redirect to the core index view
        self.assertEqual(response.status_code, 302)
        # Assert redirect to the determined index_url
        self.assertRedirects(response, self.index_url)

        # Check for the error message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Service booking is currently disabled.")
        self.assertEqual(messages[0].level, messages[0].ERROR)

    def test_booking_step1_post_valid_authenticated(self, mock_get_settings):
        """
        Test POST request to booking_step1 with valid data for an authenticated user.
        Should store data in session and redirect to service_step2_authenticated.
        """
        # Configure mock settings to enable booking
        mock_settings = MagicMock(spec=SiteSettings)
        mock_settings.enable_service_booking = True
        mock_get_settings.return_value = mock_settings

        # Log in the test user
        self.client.login(username='testuser', password='password')

        # Prepare valid form data
        appointment_datetime = datetime.datetime.now() + datetime.timedelta(days=7)
        valid_data = {
            'service_type': self.service_type.id,
            'appointment_datetime': appointment_datetime.strftime('%Y-%m-%d %H:%M:%S'), # Format as string
        }

        # Simulate a POST request
        response = self.client.post(self.service_step1_url, valid_data)

        # Check that the response is a redirect to service_step2_authenticated
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.service_step2_auth_url)

        # Check that the data is stored correctly in the session
        session_data = self.client.session.get(SERVICE_BOOKING_SESSION_KEY)
        self.assertIsNotNone(session_data)
        self.assertEqual(session_data.get('service_type_id'), self.service_type.id)
        # Check the datetime string format
        self.assertEqual(session_data.get('appointment_datetime_str'), appointment_datetime.isoformat())

    def test_booking_step1_post_valid_anonymous_allowed(self, mock_get_settings):
        """
        Test POST request to booking_step1 with valid data for an anonymous user when allowed.
        Should store data in session and redirect to service_step2_anonymous.
        """
        # Configure mock settings to enable booking and allow anonymous
        mock_settings = MagicMock(spec=SiteSettings)
        mock_settings.enable_service_booking = True
        mock_settings.allow_anonymous_bookings = True
        mock_get_settings.return_value = mock_settings

        # Prepare valid form data
        appointment_datetime = datetime.datetime.now() + datetime.timedelta(days=7)
        valid_data = {
            'service_type': self.service_type.id,
            'appointment_datetime': appointment_datetime.strftime('%Y-%m-%d %H:%M:%S'), # Format as string
        }

        # Simulate a POST request as an anonymous user
        response = self.client.post(self.service_step1_url, valid_data)

        # Check that the response is a redirect to service_step2_anonymous
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.service_step2_anon_url)

        # Check that the data is stored correctly in the session
        session_data = self.client.session.get(SERVICE_BOOKING_SESSION_KEY)
        self.assertIsNotNone(session_data)
        self.assertEqual(session_data.get('service_type_id'), self.service_type.id)
        # Check the datetime string format
        self.assertEqual(session_data.get('appointment_datetime_str'), appointment_datetime.isoformat())

    def test_booking_step1_post_invalid(self, mock_get_settings):
        """
        Test POST request to booking_step1 with invalid data.
        Should re-render the template with form errors and an error message.
        """
        # Configure mock settings to enable booking
        mock_settings = MagicMock(spec=SiteSettings)
        mock_settings.enable_service_booking = True
        mock_get_settings.return_value = mock_settings

        # Prepare invalid form data (missing service_type)
        invalid_data = {
            'appointment_datetime': (datetime.datetime.now() + datetime.timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S'),
        }

        # Simulate a POST request
        response = self.client.post(self.service_step1_url, invalid_data)

        # Check that the response is successful (status code 200)
        self.assertEqual(response.status_code, 200)

        # Check that the correct template is used
        self.assertTemplateUsed(response, 'service/service_details.html')

        # Check that the form in the context has errors
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())
        self.assertIn('service_type', response.context['form'].errors)

        # Check for the error message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Please correct the errors below.")
        self.assertEqual(messages[0].level, messages[0].ERROR)

        # Check that no data is stored in the session for this step if the form is invalid
        session_data = self.client.session.get(SERVICE_BOOKING_SESSION_KEY)
        # Check if session_data is not updated with invalid data,
        # but might contain data from previous steps if any.
        # A more robust test might check specific keys are NOT updated.
        # For simplicity here, we just check the form is invalid.

    def test_booking_step1_post_disabled(self, mock_get_settings):
        """
        Test POST request to booking_step1 when service booking is disabled.
        Should redirect to the index page and show an error message.
        """
        # Configure mock settings to disable booking
        mock_settings = MagicMock(spec=SiteSettings)
        mock_settings.enable_service_booking = False
        mock_get_settings.return_value = mock_settings

        # Prepare some dummy data
        valid_data = {
            'service_type': self.service_type.id,
            'appointment_datetime': (datetime.datetime.now() + datetime.timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S'),
        }

        # Simulate a POST request
        response = self.client.post(self.service_step1_url, valid_data)

        # Check that the response is a redirect to the core index view
        self.assertEqual(response.status_code, 302)
        # Assert redirect to the determined index_url
        self.assertRedirects(response, self.index_url)

        # Check for the error message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Service booking is currently disabled.")
        self.assertEqual(messages[0].level, messages[0].ERROR)

    def test_booking_step1_post_anonymous_not_allowed(self, mock_get_settings):
        """
        Test POST request to booking_step1 for an anonymous user when anonymous bookings are NOT allowed.
        Should redirect to the login page.
        """
        # Configure mock settings to enable booking but NOT allow anonymous
        mock_settings = MagicMock(spec=SiteSettings)
        mock_settings.enable_service_booking = True
        mock_settings.allow_anonymous_bookings = False
        mock_get_settings.return_value = mock_settings

        # Prepare valid form data
        appointment_datetime = datetime.datetime.now() + datetime.timedelta(days=7)
        valid_data = {
            'service_type': self.service_type.id,
            'appointment_datetime': appointment_datetime.strftime('%Y-%m-%d %H:%M:%S'), # Format as string
        }

        # Simulate a POST request as an anonymous user
        response = self.client.post(self.service_step1_url, valid_data)

        # Check that the response is a redirect to the login page
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.login_url)

        # Check for the info message (should be the same as GET)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Please log in or register to book a service.")
        self.assertEqual(messages[0].level, messages[0].INFO)

    def test_booking_step1_get_with_session_data(self, mock_get_settings):
        """
        Test GET request to booking_step1 when session data exists from a previous visit.
        Should pre-fill the form with session data.
        """
        # Configure mock settings to enable booking and allow anonymous
        mock_settings = MagicMock(spec=SiteSettings)
        mock_settings.enable_service_booking = True
        mock_settings.allow_anonymous_bookings = True
        mock_get_settings.return_value = mock_settings

        # Log in the test user (doesn't strictly matter for pre-filling, but good to test both)
        self.client.login(username='testuser', password='password')

        # Prepare dummy session data
        appointment_datetime = datetime.datetime.now() + datetime.timedelta(days=10)
        session = self.client.session
        session[SERVICE_BOOKING_SESSION_KEY] = {
            'service_type_id': self.service_type.id,
            'appointment_datetime_str': appointment_datetime.isoformat(),
            'extra_field': 'some_value' # Include extra data to ensure it's handled
        }
        session.save()

        # Simulate a GET request
        response = self.client.get(self.service_step1_url)

        # Check that the response is successful (status code 200)
        self.assertEqual(response.status_code, 200)

        # Check that the correct template is used
        self.assertTemplateUsed(response, 'service/service_details.html')

        # Check that the form is pre-filled with session data
        form = response.context['form']
        self.assertEqual(form.initial.get('service_type'), self.service_type)
        # Check that the datetime object is correctly reconstructed
        self.assertEqual(form.initial.get('appointment_datetime'), appointment_datetime)
        # Ensure other data from session is also in initial data (though not used by this form)
        self.assertEqual(form.initial.get('extra_field'), 'some_value')

    def test_booking_step1_get_with_invalid_session_datetime(self, mock_get_settings):
        """
        Test GET request to booking_step1 when session data contains an invalid datetime string.
        Should render the form without pre-filling the datetime field.
        """
        # Configure mock settings to enable booking
        mock_settings = MagicMock(spec=SiteSettings)
        mock_settings.enable_service_booking = True
        mock_get_settings.return_value = mock_settings

        # Prepare session data with an invalid datetime string
        session = self.client.session
        session[SERVICE_BOOKING_SESSION_KEY] = {
            'service_type_id': self.service_type.id,
            'appointment_datetime_str': 'not-a-datetime', # Invalid string
        }
        session.save()

        # Simulate a GET request
        response = self.client.get(self.service_step1_url)

        # Check that the response is successful (status code 200)
        self.assertEqual(response.status_code, 200)

        # Check that the correct template is used
        self.assertTemplateUsed(response, 'service/service_details.html')

        # Check that the form is pre-filled with service_type but NOT datetime
        form = response.context['form']
        self.assertEqual(form.initial.get('service_type'), self.service_type)
        self.assertIsNone(form.initial.get('appointment_datetime')) # Datetime should not be pre-filled

    def test_booking_step1_get_with_invalid_session_service_type(self, mock_get_settings):
        """
        Test GET request to booking_step1 when session data contains an invalid service type ID.
        Should render the form without pre-filling the service type field.
        """
        # Configure mock settings to enable booking
        mock_settings = MagicMock(spec=SiteSettings)
        mock_settings.enable_service_booking = True
        mock_get_settings.return_value = mock_settings

        # Prepare session data with an invalid service type ID
        session = self.client.session
        session[SERVICE_BOOKING_SESSION_KEY] = {
            'service_type_id': 9999, # Non-existent ID
            'appointment_datetime_str': (datetime.datetime.now() + datetime.timedelta(days=10)).isoformat(),
        }
        session.save()

        # Simulate a GET request
        response = self.client.get(self.service_step1_url)

        # Check that the response is successful (status code 200)
        self.assertEqual(response.status_code, 200)

        # Check that the correct template is used
        self.assertTemplateUsed(response, 'service/service_details.html')

        # Check that the form is pre-filled with datetime but NOT service_type
        form = response.context['form']
        self.assertIsNone(form.initial.get('service_type')) # Service type should not be pre-filled
        # Check that the datetime object is correctly reconstructed
        self.assertIsNotNone(form.initial.get('appointment_datetime'))

