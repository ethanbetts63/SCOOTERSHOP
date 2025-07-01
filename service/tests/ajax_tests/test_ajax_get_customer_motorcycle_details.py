from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.http import JsonResponse
import json

                                       
from service.ajax.ajax_get_customer_motorcycle_details import get_motorcycle_details_ajax

                       
from ..test_helpers.model_factories import CustomerMotorcycleFactory, ServiceProfileFactory

class AjaxGetCustomerMotorcycleDetailsTest(TestCase):
    """
    Tests for the AJAX view `get_motorcycle_details_ajax`.
    This test suite utilizes model factories to create actual database objects
    for more realistic testing.
    """

    def setUp(self):
        """
        Set up for each test method.
        Initialize a RequestFactory to create dummy request objects.
        Create a ServiceProfile and CustomerMotorcycle using factories.
        """
        self.factory = RequestFactory()
                                          
        self.service_profile = ServiceProfileFactory()
                                                                          
        self.motorcycle = CustomerMotorcycleFactory(service_profile=self.service_profile)

    def test_get_motorcycle_details_success(self):
        """
        Test that the view correctly returns detailed information for a valid motorcycle ID.
        Uses a real motorcycle object created by a factory.
        """
                                                                            
                                                                          
        url = reverse('service:admin_api_get_motorcycle_details', args=[self.motorcycle.pk])
        request = self.factory.get(url)

                                                                   
        response = get_motorcycle_details_ajax(request, motorcycle_id=self.motorcycle.pk)

                    
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response, JsonResponse)
        content = json.loads(response.content)

                                                                           
                                                                              
        expected_details = {
            'id': self.motorcycle.pk,
            'brand': self.motorcycle.brand,
            'model': self.motorcycle.model,
            'year': int(self.motorcycle.year),                                          
            'engine_size': self.motorcycle.engine_size,
            'rego': self.motorcycle.rego,
            'vin_number': self.motorcycle.vin_number,
            'odometer': self.motorcycle.odometer,
            'transmission': self.motorcycle.transmission,
            'engine_number': self.motorcycle.engine_number,
        }
        self.assertIn('motorcycle_details', content)
        self.assertEqual(content['motorcycle_details'], expected_details)


    def test_get_motorcycle_details_not_found(self):
        """
        Test that the view returns a 404 error if the motorcycle ID does not exist.
        """
        invalid_motorcycle_id = self.motorcycle.pk + 100                                  

                                                        
        url = reverse('service:admin_api_get_motorcycle_details', args=[invalid_motorcycle_id])
        request = self.factory.get(url)

                                
        response = get_motorcycle_details_ajax(request, motorcycle_id=invalid_motorcycle_id)

                    
        self.assertEqual(response.status_code, 404)
        self.assertIsInstance(response, JsonResponse)
        content = json.loads(response.content)
        self.assertIn('error', content)
        self.assertIn('Motorcycle not found or invalid ID', content['error'])


    def test_only_get_requests_allowed(self):
        """
        Test that only GET requests are allowed for this view.
        (The @require_GET decorator handles this).
        """
                                                            
        url = reverse('service:admin_api_get_motorcycle_details', args=[self.motorcycle.pk])

                            
        request = self.factory.post(url)
        response = get_motorcycle_details_ajax(request, motorcycle_id=self.motorcycle.pk)

                                                                                    
        self.assertEqual(response.status_code, 405)
