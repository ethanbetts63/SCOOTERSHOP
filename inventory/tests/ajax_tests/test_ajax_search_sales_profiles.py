# inventory/tests/ajax_tests/test_ajax_search_sales_profiles.py

import json
from django.test import TestCase, RequestFactory
from django.urls import reverse
from inventory.ajax.ajax_search_sales_profiles import search_sales_profiles_ajax
from ..test_helpers.model_factories import UserFactory, SalesProfileFactory

class AjaxSearchSalesProfilesTest(TestCase):
    """
    Test suite for the search_sales_profiles_ajax view.
    """

    @classmethod
    def setUpTestData(cls):
        """Set up data for the whole test case"""
        cls.factory = RequestFactory()
        cls.staff_user = UserFactory(is_staff=True)
        cls.non_staff_user = UserFactory(is_staff=False)

        # Create a variety of sales profiles to test search functionality
        cls.profile1 = SalesProfileFactory(name='John Doe', email='john.doe@example.com', phone_number='111-222-3333')
        cls.profile2 = SalesProfileFactory(name='Jane Smith', email='jane.smith@email.com', phone_number='444-555-6666')
        cls.profile3 = SalesProfileFactory(name='Peter Jones', email='peter.j@test.com', phone_number='777-888-9999', address_line_1='123 Test Street')
        
    def _get_response(self, user, query_params={}):
        """Helper method to simulate a GET request to the view."""
        request = self.factory.get(reverse('inventory:admin_api_search_sales_profiles'), query_params)
        request.user = user
        return search_sales_profiles_ajax(request)

    def test_view_requires_staff_user(self):
        """
        Tests that non-staff users and anonymous users are denied access.
        """
        # Test with a non-staff user
        response = self._get_response(self.non_staff_user, {'query': 'John'})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(json.loads(response.content), {'error': 'Permission denied'})

    def test_search_returns_correct_json_structure(self):
        """
        Tests that the JSON response contains the expected keys for each profile.
        """
        response = self._get_response(self.staff_user, {'query': 'John'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('profiles', data)
        self.assertEqual(len(data['profiles']), 1)
        
        profile_data = data['profiles'][0]
        expected_keys = ['id', 'name', 'email', 'phone_number']
        for key in expected_keys:
            self.assertIn(key, profile_data)

    def test_search_by_name(self):
        """
        Tests searching by the profile's name (case-insensitive).
        """
        response = self._get_response(self.staff_user, {'query': 'smith'})
        data = json.loads(response.content)
        self.assertEqual(len(data['profiles']), 1)
        self.assertEqual(data['profiles'][0]['id'], self.profile2.pk)

    def test_search_by_email(self):
        """
        Tests searching by the profile's email address.
        """
        response = self._get_response(self.staff_user, {'query': 'peter.j@test.com'})
        data = json.loads(response.content)
        self.assertEqual(len(data['profiles']), 1)
        self.assertEqual(data['profiles'][0]['id'], self.profile3.pk)

    def test_search_by_phone_number(self):
        """
        Tests searching by the profile's phone number.
        """
        response = self._get_response(self.staff_user, {'query': '111-222'})
        data = json.loads(response.content)
        self.assertEqual(len(data['profiles']), 1)
        self.assertEqual(data['profiles'][0]['id'], self.profile1.pk)

    def test_search_by_address(self):
        """
        Tests that the search can find a profile by their address.
        """
        response = self._get_response(self.staff_user, {'query': 'Test Street'})
        data = json.loads(response.content)
        self.assertEqual(len(data['profiles']), 1)
        self.assertEqual(data['profiles'][0]['id'], self.profile3.pk)

    def test_search_with_no_query_returns_empty_list(self):
        """
        Tests that an empty search query returns an empty list of profiles.
        """
        response = self._get_response(self.staff_user, {'query': ''})
        data = json.loads(response.content)
        self.assertEqual(len(data['profiles']), 0)
        
    def test_search_returns_distinct_results(self):
        """
        Tests that if a search term matches multiple fields on the same profile,
        the profile is only returned once.
        """
        # "Peter Jones" and "123 Test Street" should match profile3
        SalesProfileFactory(name='Peter Testman', email='p.jones@example.com')
        
        response = self._get_response(self.staff_user, {'query': 'Test'})
        data = json.loads(response.content)
        
        # We should get profile3 (matches 'Test Street') and 'Peter Testman'
        self.assertEqual(len(data['profiles']), 2)
        
        # Ensure profile3 is not duplicated
        ids = [p['id'] for p in data['profiles']]
        self.assertEqual(ids.count(self.profile3.pk), 1)
