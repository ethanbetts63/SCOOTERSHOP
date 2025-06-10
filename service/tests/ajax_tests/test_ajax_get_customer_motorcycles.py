from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.http import JsonResponse
import json

# Corrected import path for your factories
from ..test_helpers.model_factories import CustomerMotorcycleFactory, ServiceProfileFactory

# Import the view function to be tested
from service.ajax.ajax_get_customer_motorcycle_details import get_motorcycle_details_ajax

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
        # Create a ServiceProfile instance
        self.service_profile = ServiceProfileFactory()
        # Create a CustomerMotorcycle instance associated with the profile
        self.motorcycle = CustomerMotorcycleFactory(service_profile=self.service_profile)

    def test_get_motorcycle_details_success(self):
        """
        Test that the view correctly returns detailed information for a valid motorcycle ID.
        Uses a real motorcycle object created by a factory.
        """
        # Create a request for the specific motorcycle using its primary key
        # Using reverse is robust and recommended for URL lookups in tests
        url = reverse('service:admin_api_get_motorcycle_details', args=[self.motorcycle.pk])
        request = self.factory.get(url)

        # Call the view function with the request and motorcycle ID
        response = get_motorcycle_details_ajax(request, motorcycle_id=self.motorcycle.pk)

        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response, JsonResponse)
        content = json.loads(response.content)

        # Define the expected details based on the created factory instance
        # Ensure 'year' is an integer, as it's likely stored as such in the DB
        expected_details = {
            'id': self.motorcycle.pk,
            'brand': self.motorcycle.brand,
            'model': self.motorcycle.model,
            'year': int(self.motorcycle.year),  # Cast to int to match DB retrieval type
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
        invalid_motorcycle_id = self.motorcycle.pk + 100 # An ID that surely doesn't exist

        # Create a request for a non-existent motorcycle
        url = reverse('service:admin_api_get_motorcycle_details', args=[invalid_motorcycle_id])
        request = self.factory.get(url)

        # Call the view function
        response = get_motorcycle_details_ajax(request, motorcycle_id=invalid_motorcycle_id)

        # Assertions
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
        # Use a valid motorcycle ID, but send a POST request
        url = reverse('service:admin_api_get_motorcycle_details', args=[self.motorcycle.pk])

        # Try a POST request
        request = self.factory.post(url)
        response = get_motorcycle_details_ajax(request, motorcycle_id=self.motorcycle.pk)

        # @require_GET decorator returns 405 Method Not Allowed for non-GET requests
        self.assertEqual(response.status_code, 405)
