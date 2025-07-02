from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.http import JsonResponse
import json
from unittest.mock import patch, Mock
from datetime import date, timedelta
from django.utils import timezone

                                            
from service.ajax.ajax_admin_booking_precheck import admin_booking_precheck_ajax

                                                                                                 
from ..test_helpers.model_factories import ServiceTypeFactory

class AjaxAdminBookingPrecheckTest(TestCase):
    

    def setUp(self):
        
        self.factory = RequestFactory()
        self.service_type = ServiceTypeFactory()

                                       
        today = date.today()
        future_date = today + timedelta(days=5)
        current_time = (timezone.localtime(timezone.now()) + timedelta(minutes=10)).time()

        self.valid_form_data = {
            'service_type': self.service_type.pk,
            'service_date': future_date.strftime('%Y-%m-%d'),
            'dropoff_date': future_date.strftime('%Y-%m-%d'),
            'dropoff_time': current_time.strftime('%H:%M'),
            'booking_status': 'pending',
            'payment_status': 'unpaid',
            'customer_notes': 'Some notes',
            'admin_notes': 'Internal notes',
            'estimated_pickup_date': (future_date + timedelta(days=2)).strftime('%Y-%m-%d'),
        }

    @patch('service.ajax.ajax_admin_booking_precheck.AdminBookingDetailsForm')
    def test_precheck_success_no_warnings(self, MockAdminBookingDetailsForm):
        
                                          
        mock_form_instance = Mock()
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.get_warnings.return_value = []
        MockAdminBookingDetailsForm.return_value = mock_form_instance

                               
        url = reverse('service:admin_api_booking_precheck')                                                  
        request = self.factory.post(url, self.valid_form_data)

                                
        response = admin_booking_precheck_ajax(request)

                    
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response, JsonResponse)
        content = json.loads(response.content)

        self.assertEqual(content['status'], 'success')
        self.assertEqual(content['errors'], {})
        self.assertEqual(content['warnings'], [])
        MockAdminBookingDetailsForm.assert_called_once_with(request.POST)
        mock_form_instance.is_valid.assert_called_once()
        mock_form_instance.get_warnings.assert_called_once()

    @patch('service.ajax.ajax_admin_booking_precheck.AdminBookingDetailsForm')
    def test_precheck_success_with_warnings(self, MockAdminBookingDetailsForm):
        
                                          
        mock_form_instance = Mock()
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.get_warnings.return_value = ['Warning: Service date is in the past.', 'Warning: Drop-off time for today is in the past.']
        MockAdminBookingDetailsForm.return_value = mock_form_instance

                                                                                    
        url = reverse('service:admin_api_booking_precheck')
        request = self.factory.post(url, self.valid_form_data)

                                
        response = admin_booking_precheck_ajax(request)

                    
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response, JsonResponse)
        content = json.loads(response.content)

        self.assertEqual(content['status'], 'warnings')
        self.assertEqual(content['errors'], {})
        self.assertEqual(len(content['warnings']), 2)
        self.assertIn('Warning: Service date is in the past.', content['warnings'])
        self.assertIn('Warning: Drop-off time for today is in the past.', content['warnings'])
        MockAdminBookingDetailsForm.assert_called_once_with(request.POST)
        mock_form_instance.is_valid.assert_called_once()
        mock_form_instance.get_warnings.assert_called_once()


    @patch('service.ajax.ajax_admin_booking_precheck.AdminBookingDetailsForm')
    def test_precheck_form_errors(self, MockAdminBookingDetailsForm):
        
                                          
        mock_form_instance = Mock()
        mock_form_instance.is_valid.return_value = False
        mock_form_instance.errors.as_json.return_value = json.dumps({
            'service_type': [{'message': 'This field is required.', 'code': 'required'}],
            'service_date': [{'message': 'This field is required.', 'code': 'required'}],
        })
        MockAdminBookingDetailsForm.return_value = mock_form_instance

                                                              
        url = reverse('service:admin_api_booking_precheck')
        request = self.factory.post(url, {})             

                                
        response = admin_booking_precheck_ajax(request)

                    
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response, JsonResponse)
        content = json.loads(response.content)

        self.assertEqual(content['status'], 'errors')
        self.assertIn('admin_booking_details', content['errors'])
                                                                 
        self.assertIsInstance(json.loads(content['errors']['admin_booking_details']), dict)
        self.assertIn('service_type', json.loads(content['errors']['admin_booking_details']))
        self.assertIn('service_date', json.loads(content['errors']['admin_booking_details']))
        self.assertEqual(content['warnings'], [])                                  
        MockAdminBookingDetailsForm.assert_called_once_with(request.POST)
        mock_form_instance.is_valid.assert_called_once()
        mock_form_instance.errors.as_json.assert_called_once()
        mock_form_instance.get_warnings.assert_not_called()                                                 

    def test_only_post_requests_allowed(self):
        
        url = reverse('service:admin_api_booking_precheck')
                           
        request = self.factory.get(url)

                                
        response = admin_booking_precheck_ajax(request)

                                                                            
        self.assertEqual(response.status_code, 405)

