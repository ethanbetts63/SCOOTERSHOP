from django.test import TestCase, Client
from django.urls import reverse, NoReverseMatch
from unittest.mock import patch, MagicMock
import datetime
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.contrib.messages import constants as messages_constants
from django.utils import timezone

from service.models import ServiceType, CustomerMotorcycle, ServiceBooking
from service.forms import (
    ServiceDetailsForm,
    CustomerMotorcycleForm,
    ServiceBookingUserForm,
    ExistingCustomerMotorcycleForm,
)
from dashboard.models import SiteSettings

User = get_user_model()

SERVICE_BOOKING_SESSION_KEY = 'service_booking_data'

@patch('service.views.booking.SiteSettings.get_settings')
class BookingGeneralViewsTestCase(TestCase):

    def setUp(self):
        self.client = Client()

        self.user = User.objects.create_user(username='testuser', password='password', email='test@example.com')

        self.service_type = ServiceType.objects.create(
            name='Standard Service',
            description='A standard motorcycle service.',
            estimated_duration=datetime.timedelta(hours=2),
            base_price=150.00,
            is_active=True
        )

        self.service_start_url = reverse('service:service_start')
        self.service_step1_url = reverse('service:service_step1')
        self.service_step2_auth_url = reverse('service:service_step2_authenticated')
        self.service_step2_anon_url = reverse('service:service_step2_anonymous')
        self.service_info_url = reverse('service:service')
        try:
            self.index_url = reverse('core:index')
        except NoReverseMatch:
            self.index_url = '/'
        try:
             self.login_url = reverse('users:login')
        except NoReverseMatch:
             self.login_url = '/login/'

    # Test that booking_start redirects to service_step1 when booking is enabled.
    def test_booking_start_redirects_to_step1_when_enabled(self, mock_get_settings):
        mock_settings = MagicMock(spec=SiteSettings)
        mock_settings.enable_service_booking = True
        mock_get_settings.return_value = mock_settings

        response = self.client.get(self.service_start_url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.service_step1_url)

        self.assertNotIn(SERVICE_BOOKING_SESSION_KEY, self.client.session)

    # Test that booking_start redirects to index and shows a message when booking is disabled.
    def test_booking_start_redirects_to_index_when_disabled(self, mock_get_settings):
        mock_settings = MagicMock(spec=SiteSettings)
        mock_settings.enable_service_booking = False
        mock_get_settings.return_value = mock_settings

        response = self.client.get(self.service_start_url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.index_url)

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Service booking is currently disabled.")
        self.assertEqual(messages[0].level, messages_constants.ERROR)

        self.assertNotIn(SERVICE_BOOKING_SESSION_KEY, self.client.session)

    # Test that booking_start always clears the service booking session key.
    def test_booking_start_clears_session(self, mock_get_settings):
        mock_settings = MagicMock(spec=SiteSettings)
        mock_settings.enable_service_booking = True
        mock_get_settings.return_value = mock_settings

        session = self.client.session
        session[SERVICE_BOOKING_SESSION_KEY] = {'dummy_data': 'test'}
        session.save()

        response = self.client.get(self.service_start_url)

        self.assertNotIn(SERVICE_BOOKING_SESSION_KEY, self.client.session)

    # Test for service_confirmed_view basic rendering
    def test_service_confirmed_view(self, mock_get_settings):
        mock_settings = MagicMock(spec=SiteSettings)
        mock_settings.enable_service_booking = True
        mock_get_settings.return_value = mock_settings

        response = self.client.get(reverse('service:service_confirmed'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service/service_not_yet_confirmed.html')


@patch('service.views.service.SiteSettings.get_settings')
class ServiceInfoViewsTestCase(TestCase):
    
    def setUp(self):
        self.client = Client()
        
        # Create some test service types
        self.active_service_type = ServiceType.objects.create(
            name='Regular Service',
            description='A regular motorcycle service.',
            estimated_duration=datetime.timedelta(hours=1),
            base_price=100.00,
            is_active=True
        )
        
        self.inactive_service_type = ServiceType.objects.create(
            name='Premium Service',
            description='A premium motorcycle service.',
            estimated_duration=datetime.timedelta(hours=3),
            base_price=250.00,
            is_active=False
        )
        
        self.service_info_url = reverse('service:service')
        try:
            self.index_url = reverse('core:index')
        except NoReverseMatch:
            self.index_url = '/'
    
    # Test that service info page loads correctly when enabled
    def test_service_info_page_loads_when_enabled(self, mock_get_settings):
        mock_settings = MagicMock(spec=SiteSettings)
        mock_settings.enable_service_booking = True
        mock_get_settings.return_value = mock_settings
        
        response = self.client.get(self.service_info_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service/service.html')
        
        # Check that only active service types are displayed
        self.assertIn(self.active_service_type, response.context['service_types'])
        self.assertNotIn(self.inactive_service_type, response.context['service_types'])
        
    # Test that service info page redirects to index when disabled
    def test_service_info_redirects_when_disabled(self, mock_get_settings):
        mock_settings = MagicMock(spec=SiteSettings)
        mock_settings.enable_service_booking = False
        mock_get_settings.return_value = mock_settings
        
        response = self.client.get(self.service_info_url)
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.index_url)
        
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Service information is currently disabled.")
        self.assertEqual(messages[0].level, messages_constants.ERROR)
    
    # Test handling of database errors when fetching service types
    @patch('service.views.service.ServiceType.objects.filter')
    def test_service_info_handles_db_errors(self, mock_filter, mock_get_settings):
        mock_settings = MagicMock(spec=SiteSettings)
        mock_settings.enable_service_booking = True
        mock_get_settings.return_value = mock_settings
        
        # Simulate a database error
        mock_filter.side_effect = Exception("Database error")
        
        response = self.client.get(self.service_info_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service/service.html')
        
        # Check that service_types is an empty list when there's an error
        self.assertEqual(response.context['service_types'], [])
        
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Could not load service types.")