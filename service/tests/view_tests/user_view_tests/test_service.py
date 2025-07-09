from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch, MagicMock
from service.models import ServiceType, TempServiceBooking, ServiceSettings, Servicefaq
from dashboard.models import SiteSettings
from service.tests.test_helpers.model_factories import ServiceTypeFactory, TempServiceBookingFactory, ServiceSettingsFactory, ServicefaqFactory, SiteSettingsFactory
from django.contrib.messages import get_messages
import datetime

class ServiceViewTest(TestCase):

    def setUp(self):
        self.site_settings = SiteSettingsFactory(enable_service_booking=True)
        self.service_settings = ServiceSettingsFactory()
        self.service_type = ServiceTypeFactory()
        self.service_faq = ServicefaqFactory()

    @patch('service.views.user_views.service.get_service_date_availability')
    def test_get_service_view_success(self, mock_get_service_date_availability):
        mock_get_service_date_availability.return_value = (datetime.date.today(), '[]')
        response = self.client.get(reverse('service:service'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service/service.html')
        self.assertIn('service_types', response.context)
        self.assertIn('service_faqs', response.context)
        self.assertIn('form', response.context)
        self.assertIn('service_settings', response.context)
        self.assertIn('blocked_service_dates_json', response.context)
        self.assertIn('min_service_date_flatpickr', response.context)
        self.assertIn('temp_service_booking', response.context)

    def test_get_service_view_service_booking_disabled(self):
        self.site_settings.enable_service_booking = False
        self.site_settings.save()
        response = self.client.get(reverse('service:service'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:index'))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('Service information is currently disabled.', str(messages[0]))

    @patch('service.views.user_views.service.ServiceType.objects.filter')
    @patch('service.views.user_views.service.get_service_date_availability')
    def test_get_service_view_service_types_load_error(self, mock_get_service_date_availability, mock_service_type_filter):
        mock_get_service_date_availability.return_value = (datetime.date.today(), '[]')
        mock_service_type_filter.side_effect = Exception("DB Error")
        response = self.client.get(reverse('service:service'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service/service.html')
        self.assertEqual(len(response.context['service_types']), 0)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('Could not load service types.', str(messages[0]))

    @patch('service.views.user_views.service.Servicefaq.objects.filter')
    @patch('service.views.user_views.service.get_service_date_availability')
    def test_get_service_view_service_faqs_load_error(self, mock_get_service_date_availability, mock_service_faq_filter):
        mock_get_service_date_availability.return_value = (datetime.date.today(), '[]')
        mock_service_faq_filter.side_effect = Exception("DB Error")
        response = self.client.get(reverse('service:service'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service/service.html')
        self.assertEqual(len(response.context['service_faqs']), 0)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('Could not load service faqs.', str(messages[0]))

    @patch('service.views.user_views.service.get_service_date_availability')
    def test_get_service_view_with_temp_booking_in_session(self, mock_get_service_date_availability):
        mock_get_service_date_availability.return_value = (datetime.date.today(), '[]')
        temp_booking = TempServiceBookingFactory(service_type=self.service_type, service_date=datetime.date.today())
        self.client.session['temp_service_booking_uuid'] = str(temp_booking.session_uuid)
        response = self.client.get(reverse('service:service'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service/service.html')
        self.assertEqual(response.context['temp_service_booking'], temp_booking)
        self.assertEqual(response.context['form'].initial['service_type'], self.service_type)
        self.assertEqual(response.context['form'].initial['service_date'], datetime.date.today())

    @patch('service.views.user_views.service.get_service_date_availability')
    def test_get_service_view_with_invalid_temp_booking_uuid_in_session(self, mock_get_service_date_availability):
        mock_get_service_date_availability.return_value = (datetime.date.today(), '[]')
        self.client.session['temp_service_booking_uuid'] = 'invalid-uuid'
        response = self.client.get(reverse('service:service'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service/service.html')
        self.assertIsNone(response.context['temp_service_booking'])
        self.assertNotIn('temp_service_booking_uuid', self.client.session)