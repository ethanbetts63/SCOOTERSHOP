from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
import datetime
import json

                              
from service.models import ServiceType

                                                       
from service.tests.test_helpers.model_factories import ServiceTypeFactory

class AjaxGetEstimatedPickupDateTest(TestCase):
    """
    Tests for the ajax_get_estimated_pickup_date view.
    """

    def setUp(self):
        """
        Set up for each test method.
        """
        self.client = Client()
                                                        
        self.url = reverse('service:admin_api_get_estimated_pickup_date') 

                                                   
        self.service_type = ServiceTypeFactory(estimated_duration=3)
        self.service_type_zero_duration = ServiceTypeFactory(estimated_duration=0)

                                           
        self.test_service_date = datetime.date(2025, 10, 20)                   

    def test_valid_request(self):
        """
        Test that a valid GET request returns the correct estimated pickup date.
        """
        response = self.client.get(
            self.url,
            {
                'service_type_id': self.service_type.pk,
                'service_date': self.test_service_date.strftime('%Y-%m-%d')
            }
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        expected_pickup_date = self.test_service_date + datetime.timedelta(days=self.service_type.estimated_duration)
        self.assertEqual(data['estimated_pickup_date'], expected_pickup_date.strftime('%Y-%m-%d'))

    def test_valid_request_zero_duration(self):
        """
        Test that a valid GET request with zero estimated duration returns
        the service date as the pickup date.
        """
        response = self.client.get(
            self.url,
            {
                'service_type_id': self.service_type_zero_duration.pk,
                'service_date': self.test_service_date.strftime('%Y-%m-%d')
            }
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

                                                                     
        self.assertEqual(data['estimated_pickup_date'], self.test_service_date.strftime('%Y-%m-%d'))

    def test_missing_service_type_id(self):
        """
        Test that the view returns a 400 error if 'service_type_id' is missing.
        """
        response = self.client.get(
            self.url,
            {
                'service_date': self.test_service_date.strftime('%Y-%m-%d')
            }
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['error'], 'Missing service_type_id or service_date')

    def test_missing_service_date(self):
        """
        Test that the view returns a 400 error if 'service_date' is missing.
        """
        response = self.client.get(
            self.url,
            {
                'service_type_id': self.service_type.pk
            }
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['error'], 'Missing service_type_id or service_date')

    def test_service_type_not_found(self):
        """
        Test that the view returns a 404 error if the service_type_id does not exist.
        """
        non_existent_id = self.service_type.pk + 999                    
        response = self.client.get(
            self.url,
            {
                'service_type_id': non_existent_id,
                'service_date': self.test_service_date.strftime('%Y-%m-%d')
            }
        )

                                                                                            
        self.assertEqual(response.status_code, 404) 
        data = response.json()
        self.assertEqual(data['error'], 'ServiceType not found')

    def test_invalid_date_format(self):
        """
        Test that the view returns a 400 error for an invalid 'service_date' format.
        """
        response = self.client.get(
            self.url,
            {
                'service_type_id': self.service_type.pk,
                'service_date': '2025/10/20'                 
            }
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
                                                                             
        self.assertEqual(data['error'], 'Invalid date format. ExpectedYYYY-MM-DD.')

                                                                
    @patch('service.ajax.ajax_get_estimated_pickup_date.calculate_estimated_pickup_date') 
    def test_calculate_estimated_pickup_date_utility_error(self, mock_calculate):
        """
        Test that if calculate_estimated_pickup_date utility returns None,
        the AJAX view returns a 500 error.
        """
        mock_calculate.return_value = None                                            

        response = self.client.get(
            self.url,
            {
                'service_type_id': self.service_type.pk,
                'service_date': self.test_service_date.strftime('%Y-%m-%d')
            }
        )

                                                           
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertEqual(data['error'], 'Could not calculate estimated pickup date')
        mock_calculate.assert_called_once()                                         

                                                                                                              
    @patch('service.models.ServiceType.objects.get') 
    def test_unexpected_exception(self, mock_get_service_type):
        """
        Test that an unexpected exception during ServiceType retrieval
        results in a 500 error.
        """
        mock_get_service_type.side_effect = Exception("Database connection error")

        response = self.client.get(
            self.url,
            {
                'service_type_id': self.service_type.pk,
                'service_date': self.test_service_date.strftime('%Y-%m-%d')
            }
        )

                                                                        
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertEqual(data['error'], 'An unexpected error occurred: Database connection error')

