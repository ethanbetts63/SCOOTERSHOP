# inventory/tests/ajax_tests/test_ajax_search_motorcycles.py

import json
from django.test import TestCase, RequestFactory
from django.urls import reverse
from inventory.ajax.ajax_search_motorcycles import search_motorcycles_ajax
from ..test_helpers.model_factories import UserFactory, MotorcycleFactory

class AjaxSearchMotorcyclesTest(TestCase):
    """
    Test suite for the search_motorcycles_ajax view.
    """

    @classmethod
    def setUpTestData(cls):
        """Set up data for the whole test case"""
        cls.factory = RequestFactory()
        cls.staff_user = UserFactory(is_staff=True)
        cls.non_staff_user = UserFactory(is_staff=False)

        # Create a variety of motorcycles to test search and filtering
        cls.honda_crf = MotorcycleFactory(brand='Honda', model='CRF450R', title='2023 Honda CRF450R', rego='CRF450', stock_number='S101', vin_number='VIN101', status='for_sale')
        cls.yamaha_yz = MotorcycleFactory(brand='Yamaha', model='YZ250F', title='2022 Yamaha YZ250F', rego='YZ250', stock_number='S102', vin_number='VIN102', status='for_sale')
        cls.kawasaki_kx = MotorcycleFactory(brand='Kawasaki', model='KX450', title='2023 Kawasaki KX450', rego='KX450', stock_number='S103', vin_number='VIN103', status='reserved')
        cls.suzuki_rmz = MotorcycleFactory(brand='Suzuki', model='RM-Z250', title='2021 Suzuki RM-Z250', rego='RMZ250', stock_number='S104', vin_number='VIN104', status='sold')
        cls.ktm_sxf = MotorcycleFactory(brand='KTM', model='350 SX-F', title='2024 KTM 350 SX-F', rego='KTM350', stock_number='S105', vin_number='VIN105', status='unavailable')
        
    def _get_response(self, user, query_params={}):
        """Helper method to simulate a GET request to the view."""
        # FIX: Corrected the URL name to match urls.py
        request = self.factory.get(reverse('inventory:admin_api_search_motorcycles'), query_params)
        request.user = user
        return search_motorcycles_ajax(request)

    def test_view_requires_staff_user(self):
        """
        Tests that non-staff users and anonymous users are denied access.
        """
        response = self._get_response(self.non_staff_user, {'query': 'Honda'})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(json.loads(response.content), {'error': 'Permission denied'})
        
    def test_search_returns_correct_json_structure(self):
        """
        Tests that the JSON response contains the expected keys for each motorcycle.
        """
        response = self._get_response(self.staff_user, {'query': 'Honda'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('motorcycles', data)
        self.assertEqual(len(data['motorcycles']), 1)
        
        motorcycle_data = data['motorcycles'][0]
        expected_keys = ['id', 'title', 'brand', 'model', 'year', 'status', 'is_available', 'quantity', 'condition', 'price', 'rego', 'stock_number']
        for key in expected_keys:
            self.assertIn(key, motorcycle_data)

    def test_search_by_brand_model_and_title(self):
        """
        Tests searching by various text fields like brand, model, and title.
        """
        response = self._get_response(self.staff_user, {'query': 'yamaha'})
        data = json.loads(response.content)
        self.assertEqual(len(data['motorcycles']), 1)
        self.assertEqual(data['motorcycles'][0]['id'], self.yamaha_yz.pk)
        
        response = self._get_response(self.staff_user, {'query': 'CRF450R'})
        data = json.loads(response.content)
        self.assertEqual(len(data['motorcycles']), 1)
        self.assertEqual(data['motorcycles'][0]['id'], self.honda_crf.pk)

        response = self._get_response(self.staff_user, {'query': '2023'})
        data = json.loads(response.content)
        self.assertEqual(len(data['motorcycles']), 2)

    def test_search_by_identifiers_pk_rego_vin_stock(self):
        """
        Tests searching by unique identifiers like PK, rego, VIN, and stock number.
        """
        response = self._get_response(self.staff_user, {'query': str(self.kawasaki_kx.pk)})
        data = json.loads(response.content)
        self.assertEqual(len(data['motorcycles']), 1)
        self.assertEqual(data['motorcycles'][0]['id'], self.kawasaki_kx.pk)

        response = self._get_response(self.staff_user, {'query': 'YZ250'})
        data = json.loads(response.content)
        self.assertEqual(len(data['motorcycles']), 1)
        self.assertEqual(data['motorcycles'][0]['id'], self.yamaha_yz.pk)

        response = self._get_response(self.staff_user, {'query': 'VIN101'})
        data = json.loads(response.content)
        self.assertEqual(len(data['motorcycles']), 1)
        self.assertEqual(data['motorcycles'][0]['id'], self.honda_crf.pk)

        response = self._get_response(self.staff_user, {'query': 'S103'})
        data = json.loads(response.content)
        self.assertEqual(len(data['motorcycles']), 1)
        self.assertEqual(data['motorcycles'][0]['id'], self.kawasaki_kx.pk)

    def test_default_search_excludes_unavailable_and_sold(self):
        """
        Tests that by default, the search results do not include motorcycles with
        'sold' or 'unavailable' statuses.
        """
        response = self._get_response(self.staff_user, {'query': '20'}) 
        data = json.loads(response.content)
        
        self.assertEqual(len(data['motorcycles']), 3)
        returned_ids = {m['id'] for m in data['motorcycles']}
        self.assertIn(self.honda_crf.pk, returned_ids)
        self.assertIn(self.yamaha_yz.pk, returned_ids)
        self.assertIn(self.kawasaki_kx.pk, returned_ids)
        self.assertNotIn(self.suzuki_rmz.pk, returned_ids)
        self.assertNotIn(self.ktm_sxf.pk, returned_ids)

    def test_search_includes_all_with_include_unavailable_flag(self):
        """
        Tests that setting 'include_unavailable=true' returns motorcycles of all statuses.
        """
        query_params = {'query': '20', 'include_unavailable': 'true'}
        response = self._get_response(self.staff_user, query_params)
        data = json.loads(response.content)
        
        self.assertEqual(len(data['motorcycles']), 5)
        returned_ids = {m['id'] for m in data['motorcycles']}
        self.assertIn(self.suzuki_rmz.pk, returned_ids)
        self.assertIn(self.ktm_sxf.pk, returned_ids)

    def test_search_with_no_query_returns_empty_list(self):
        """
        Tests that an empty search query returns an empty list of motorcycles.
        """
        response = self._get_response(self.staff_user, {'query': ''})
        data = json.loads(response.content)
        self.assertEqual(len(data['motorcycles']), 0)
