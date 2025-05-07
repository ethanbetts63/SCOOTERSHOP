from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
import datetime
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.contrib.messages import constants as messages_constants

from service.models import ServiceType
from service.forms import ServiceDetailsForm
from dashboard.models import SiteSettings

User = get_user_model()

SERVICE_BOOKING_SESSION_KEY = 'service_booking_data'

@patch('service.views.booking.SiteSettings.get_settings')
class BookingStep1TestCase(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='password',
            email='test@example.com'
        )

        self.service_type = ServiceType.objects.create(
            name='Standard Service',
            description='A standard motorcycle service.',
            estimated_duration=datetime.timedelta(hours=2),
            base_price=150.00,
            is_active=True
        )

        # Common URLs
        self.step1_url = reverse('service:service_step1')
        self.step2_auth_url = reverse('service:service_step2_authenticated')
        self.step2_anon_url = reverse('service:service_step2_anonymous')
        self.index_url = reverse('core:index')
        self.login_url = reverse('users:login')

        # Valid form data - booking_comments removed as it's now in step 3
        self.tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
        self.valid_form_data = {
            'service_type': self.service_type.id,
            'appointment_date': self.tomorrow.strftime('%Y-%m-%d %H:%M:%S'),
            # 'booking_comments': 'Test notes', # Removed
        }

    # Test GET request with booking enabled
    def test_step1_get_request_when_enabled(self, mock_get_settings):
        mock_settings = MagicMock(spec=SiteSettings)
        mock_settings.enable_service_booking = True
        mock_settings.allow_anonymous_bookings = True
        mock_get_settings.return_value = mock_settings

        response = self.client.get(self.step1_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service/service_details.html')
        self.assertIsInstance(response.context['form'], ServiceDetailsForm)
        self.assertEqual(response.context['step'], 1)
        self.assertEqual(response.context['total_steps'], 3)

    # Test GET request with booking disabled
    def test_step1_get_request_when_disabled(self, mock_get_settings):
        mock_settings = MagicMock(spec=SiteSettings)
        mock_settings.enable_service_booking = False
        mock_get_settings.return_value = mock_settings

        response = self.client.get(self.step1_url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.index_url)

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Service booking is currently disabled.")
        self.assertEqual(messages[0].level, messages_constants.ERROR)

    # Test anonymous access when not allowed
    def test_step1_anonymous_access_when_not_allowed(self, mock_get_settings):
        mock_settings = MagicMock(spec=SiteSettings)
        mock_settings.enable_service_booking = True
        mock_settings.allow_anonymous_bookings = False
        mock_get_settings.return_value = mock_settings

        response = self.client.get(self.step1_url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.login_url)

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Please log in or register to book a service.")
        self.assertEqual(messages[0].level, messages_constants.INFO)

    # Test POST with valid data for authenticated user
    def test_step1_post_valid_data_authenticated(self, mock_get_settings):
        mock_settings = MagicMock(spec=SiteSettings)
        mock_settings.enable_service_booking = True
        mock_settings.allow_anonymous_bookings = True
        mock_get_settings.return_value = mock_settings

        self.client.login(username='testuser', password='password')

        response = self.client.post(self.step1_url, self.valid_form_data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.step2_auth_url)

        # Check session data
        session = self.client.session
        self.assertIn(SERVICE_BOOKING_SESSION_KEY, session)
        session_data = session[SERVICE_BOOKING_SESSION_KEY]

        self.assertEqual(session_data['service_type_id'], self.service_type.id)
        self.assertIn('appointment_date_str', session_data)
        # Removed assertion for booking_comments in step 1 session data

    # Test POST with valid data for anonymous user
    def test_step1_post_valid_data_anonymous(self, mock_get_settings):
        mock_settings = MagicMock(spec=SiteSettings)
        mock_settings.enable_service_booking = True
        mock_settings.allow_anonymous_bookings = True
        mock_get_settings.return_value = mock_settings

        response = self.client.post(self.step1_url, self.valid_form_data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.step2_anon_url)

        # Check session data
        session = self.client.session
        self.assertIn(SERVICE_BOOKING_SESSION_KEY, session)

    # Test POST with invalid service type
    def test_step1_post_invalid_service_type(self, mock_get_settings):
        mock_settings = MagicMock(spec=SiteSettings)
        mock_settings.enable_service_booking = True
        mock_settings.allow_anonymous_bookings = True
        mock_get_settings.return_value = mock_settings

        invalid_data = self.valid_form_data.copy()
        invalid_data['service_type'] = 999  # Non-existent service type ID

        response = self.client.post(self.step1_url, invalid_data)

        self.assertEqual(response.status_code, 200)  # Form validation failed
        self.assertTemplateUsed(response, 'service/service_details.html')

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Please correct the errors below" in str(msg) for msg in messages))

    # Test POST with invalid appointment datetime
    def test_step1_post_invalid_datetime(self, mock_get_settings):
        mock_settings = MagicMock(spec=SiteSettings)
        mock_settings.enable_service_booking = True
        mock_settings.allow_anonymous_bookings = True
        mock_get_settings.return_value = mock_settings

        invalid_data = self.valid_form_data.copy()
        invalid_data['appointment_date'] = 'not-a-date'

        response = self.client.post(self.step1_url, invalid_data)

        self.assertEqual(response.status_code, 200)  # Form validation failed
        self.assertTemplateUsed(response, 'service/service_details.html')

    # Test initial form data from session
    def test_step1_get_with_session_data(self, mock_get_settings):
        mock_settings = MagicMock(spec=SiteSettings)
        mock_settings.enable_service_booking = True
        mock_settings.allow_anonymous_bookings = True
        mock_get_settings.return_value = mock_settings

        # Set up session data
        session = self.client.session
        appointment_date = datetime.datetime.now() + datetime.timedelta(days=2)
        session_data = {
            'service_type_id': self.service_type.id,
            'appointment_date_str': appointment_date.isoformat(),
            # 'notes': 'Previous notes' # Removed as comments are not saved in step 1 session
        }
        session[SERVICE_BOOKING_SESSION_KEY] = session_data
        session.save()

        response = self.client.get(self.step1_url)

        self.assertEqual(response.status_code, 200)
        form = response.context['form']

        # Check that form is initialized with session data
        self.assertEqual(form.initial['service_type'], self.service_type)
        # No assertion for booking_comments initial data as it's not in this form anymore