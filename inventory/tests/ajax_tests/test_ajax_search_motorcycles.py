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

        # Create a variety of motorcycles with realistic statuses and availability
        cls.honda_crf = MotorcycleFactory(brand='Honda', model='CRF450R', status='for_sale', is_available=True, rego='HONDACRF')
        cls.yamaha_yz = MotorcycleFactory(brand='Yamaha', model='YZ250F', status='for_sale', is_available=True, vin_number='VIN_YAMAHA')
        cls.kawasaki_kx = MotorcycleFactory(brand='Kawasaki', model='KX450', status='reserved', is_available=True, stock_number='STOCK_KAWI')
        # FIX: Ensure sold/unavailable bikes have is_available=False for more realistic data
        cls.suzuki_rmz = MotorcycleFactory(brand='Suzuki', model='RM-Z250', status='sold', is_available=False)
        cls.ktm_sxf = MotorcycleFactory(brand='KTM', model='350 SX-F', status='unavailable', is_available=False)
        
    def _get_response(self, user, query_params={}):
        """Helper method to simulate a GET request to the view."""
        request = self.factory.get(reverse('inventory:admin_api_search_motorcycles'), query_params)
        request.user = user
        return search_motorcycles_ajax(request)

    def test_view_requires_staff_user(self):
        response = self._get_response(self.non_staff_user, {'query': 'Honda'})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(json.loads(response.content), {'error': 'Permission denied'})
        
    def test_search_returns_correct_json_structure(self):
        response = self._get_response(self.staff_user, {'query': 'Honda'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('motorcycles', data)
        self.assertEqual(len(data['motorcycles']), 1)
        
        motorcycle_data = data['motorcycles'][0]
        expected_keys = ['id', 'title', 'brand', 'model', 'year', 'status', 'is_available', 'quantity', 'condition', 'price', 'rego', 'stock_number']
        for key in expected_keys:
            self.assertIn(key, motorcycle_data)

    def test_search_by_identifiers_pk_rego_vin_stock(self):
        # Search by Rego
        response = self._get_response(self.staff_user, {'query': 'HONDACRF'})
        data = json.loads(response.content)
        self.assertEqual(len(data['motorcycles']), 1)
        self.assertEqual(data['motorcycles'][0]['id'], self.honda_crf.pk)

        # Search by VIN
        response = self._get_response(self.staff_user, {'query': 'VIN_YAMAHA'})
        data = json.loads(response.content)
        self.assertEqual(len(data['motorcycles']), 1)
        self.assertEqual(data['motorcycles'][0]['id'], self.yamaha_yz.pk)

        # Search by Stock Number
        response = self._get_response(self.staff_user, {'query': 'STOCK_KAWI'})
        data = json.loads(response.content)
        self.assertEqual(len(data['motorcycles']), 1)
        self.assertEqual(data['motorcycles'][0]['id'], self.kawasaki_kx.pk)

    def test_default_search_excludes_unavailable_and_sold(self):
        """
        Tests that by default, the search results do not include motorcycles with
        'sold' or 'unavailable' statuses.
        """
        response = self._get_response(self.staff_user, {'query': 'model'}) # A term to match all
        data = json.loads(response.content)
        
        # Should return 'for_sale' and 'reserved' bikes only (Honda, Yamaha, Kawasaki)
        self.assertEqual(len(data['motorcycles']), 3)
        returned_ids = {m['id'] for m in data['motorcycles']}
        self.assertIn(self.honda_crf.pk, returned_ids)
        self.assertIn(self.yamaha_yz.pk, returned_ids)
        self.assertIn(self.kawasaki_kx.pk, returned_ids)
        self.assertNotIn(self.suzuki_rmz.pk, returned_ids)
        self.assertNotIn(self.ktm_sxf.pk, returned_ids)

    def test_search_includes_all_with_include_unavailable_flag(self):
        query_params = {'query': 'model', 'include_unavailable': 'true'}
        response = self._get_response(self.staff_user, query_params)
        data = json.loads(response.content)
        
        # Should now return all 5 bikes
        self.assertEqual(len(data['motorcycles']), 5)
        returned_ids = {m['id'] for m in data['motorcycles']}
        self.assertIn(self.suzuki_rmz.pk, returned_ids)
        self.assertIn(self.ktm_sxf.pk, returned_ids)

    def test_search_with_no_query_returns_empty_list(self):
        response = self._get_response(self.staff_user, {'query': ''})
        data = json.loads(response.content)
        self.assertEqual(len(data['motorcycles']), 0)
