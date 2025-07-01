from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.http import JsonResponse
import json

                                          
from ..test_helpers.model_factories import ServiceProfileFactory, UserFactory

                                       
from service.ajax.ajax_search_service_profiles import search_customer_profiles_ajax

class AjaxSearchCustomerProfilesTest(TestCase):
    """
    Tests for the AJAX view `search_customer_profiles_ajax`.
    This test suite utilizes model factories to create actual database objects
    for more realistic testing of the search functionality.
    """

    def setUp(self):
        """
        Set up for each test method.
        Initialize a RequestFactory to create dummy request objects.
        """
        self.factory = RequestFactory()

                                                                     
        self.user1 = UserFactory(username='johndoe', email='john.doe@example.com')
        self.profile1 = ServiceProfileFactory(
            user=self.user1,
            name='John Doe',
            email='john.doe@example.com',
            phone_number='0412345678',
            city='Sydney',
            post_code='2000'
        )

        self.user2 = UserFactory(username='janedoe', email='jane.doe@test.com')
        self.profile2 = ServiceProfileFactory(
            user=self.user2,
            name='Jane Smith',
            email='jane.smith@example.com',
            phone_number='0498765432',
            city='Melbourne',
            address_line_1='123 Main St'
        )

        self.user3 = UserFactory(username='bobjohnson', email='bob.j@other.com')                                   
        self.profile3 = ServiceProfileFactory(
            user=self.user3,
            name='Bob Johnson',                                                               
            email='bob.j@other.com',
            phone_number='0455551111',
            city='Sydney',
            country='Australia'
        )

        self.user4 = UserFactory(username='alice', email='alice@unique.com')
        self.profile4 = ServiceProfileFactory(                                           
            user=self.user4,
            name='Alice Wonderland',
            email='alice@unique.com',
            phone_number='0400000000',
            city='Brisbane'
        )

    def test_search_customer_profiles_by_name(self):
        """
        Test searching for customer profiles by name.
        Uses a specific name to ensure only one match.
        """
        search_term = "John Doe"                                          
        url = reverse('service:admin_api_search_customer') + f'?query={search_term}'
        request = self.factory.get(url)
        response = search_customer_profiles_ajax(request)

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response, JsonResponse)
        content = json.loads(response.content)

        self.assertIn('profiles', content)
        self.assertEqual(len(content['profiles']), 1)
        self.assertEqual(content['profiles'][0]['name'], self.profile1.name)
        self.assertEqual(content['profiles'][0]['email'], self.profile1.email)
        self.assertEqual(content['profiles'][0]['phone_number'], self.profile1.phone_number)

    def test_search_customer_profiles_by_email(self):
        """
        Test searching for customer profiles by email.
        """
        search_term = "jane.doe@test.com"                                    
        url = reverse('service:admin_api_search_customer') + f'?query={search_term}'
        request = self.factory.get(url)
        response = search_customer_profiles_ajax(request)

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response, JsonResponse)
        content = json.loads(response.content)

        self.assertIn('profiles', content)
        self.assertEqual(len(content['profiles']), 1)
        self.assertEqual(content['profiles'][0]['name'], self.profile2.name)

    def test_search_customer_profiles_by_phone_number(self):
        """
        Test searching for customer profiles by phone number.
        """
        search_term = "045555"
        url = reverse('service:admin_api_search_customer') + f'?query={search_term}'
        request = self.factory.get(url)
        response = search_customer_profiles_ajax(request)

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response, JsonResponse)
        content = json.loads(response.content)

        self.assertIn('profiles', content)
        self.assertEqual(len(content['profiles']), 1)
        self.assertEqual(content['profiles'][0]['name'], self.profile3.name)

    def test_search_customer_profiles_multiple_matches_and_ordering(self):
        """
        Test searching where multiple profiles match, ensuring correct ordering (by name).
        """
        search_term = "Sydney"                                           
        url = reverse('service:admin_api_search_customer') + f'?query={search_term}'
        request = self.factory.get(url)
        response = search_customer_profiles_ajax(request)

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response, JsonResponse)
        content = json.loads(response.content)

        self.assertIn('profiles', content)
        self.assertEqual(len(content['profiles']), 2)

                                                                           
        self.assertEqual(content['profiles'][0]['name'], self.profile3.name)              
        self.assertEqual(content['profiles'][1]['name'], self.profile1.name)           

    def test_search_customer_profiles_no_matches(self):
        """
        Test searching for a term that should yield no matches.
        """
        search_term = "NonExistentCustomer"
        url = reverse('service:admin_api_search_customer') + f'?query={search_term}'
        request = self.factory.get(url)
        response = search_customer_profiles_ajax(request)

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response, JsonResponse)
        content = json.loads(response.content)

        self.assertIn('profiles', content)
        self.assertEqual(len(content['profiles']), 0)
        self.assertEqual(content['profiles'], [])

    def test_search_customer_profiles_empty_query(self):
        """
        Test that an empty search query returns an empty list of profiles.
        """
        url = reverse('service:admin_api_search_customer') + '?query='
        request = self.factory.get(url)
        response = search_customer_profiles_ajax(request)

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response, JsonResponse)
        content = json.loads(response.content)

        self.assertIn('profiles', content)
        self.assertEqual(len(content['profiles']), 0)
        self.assertEqual(content['profiles'], [])

    def test_search_customer_profiles_no_query_parameter(self):
        """
        Test that no 'query' parameter also returns an empty list of profiles.
        """
        url = reverse('service:admin_api_search_customer')
        request = self.factory.get(url)
        response = search_customer_profiles_ajax(request)

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response, JsonResponse)
        content = json.loads(response.content)                 

        self.assertIn('profiles', content)
        self.assertEqual(len(content['profiles']), 0)
        self.assertEqual(content['profiles'], [])

    def test_only_get_requests_allowed(self):
        """
        Test that only GET requests are allowed for this view.
        (The @require_GET decorator handles this).
        """
        url = reverse('service:admin_api_search_customer')
        request = self.factory.post(url)                      

        response = search_customer_profiles_ajax(request)

                                                                                    
        self.assertEqual(response.status_code, 405)

