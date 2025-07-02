import json
from django.test import TestCase, Client
from django.urls import reverse
from inventory.models import Motorcycle, MotorcycleCondition
from ..test_helpers.model_factories import MotorcycleFactory

class AjaxGetMotorcycleListTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.client = Client()

        MotorcycleFactory(
            condition='new',
            title="New Bike by Field",
            status='for_sale'
        )
        MotorcycleFactory(
            conditions=['new'],
            title="New Bike by M2M",
            status='for_sale'
        )
        MotorcycleFactory(
            condition='used',
            title="Used Bike by Field",
            status='for_sale'
        )
        MotorcycleFactory(
            conditions=['used'],
            title="Used Bike by M2M",
            status='for_sale'
        )
        MotorcycleFactory(
            condition='new',
            title="Unavailable New Bike",
            is_available=False,
            status='sold'
        )

    def test_get_all_motorcycles(self):
        response = self.client.get(reverse('inventory:ajax-get-motorcycle-list'), {'condition_slug': 'all'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['motorcycles']), 4)
        titles = [m['title'] for m in data['motorcycles']]
        self.assertNotIn("Unavailable New Bike", titles)

    def test_get_new_motorcycles(self):
        response = self.client.get(reverse('inventory:ajax-get-motorcycle-list'), {'condition_slug': 'new'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['motorcycles']), 2)
        titles = {m['title'] for m in data['motorcycles']}
        self.assertIn("New Bike by Field", titles)
        self.assertIn("New Bike by M2M", titles)

    def test_get_used_motorcycles(self):
        response = self.client.get(reverse('inventory:ajax-get-motorcycle-list'), {'condition_slug': 'used'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['motorcycles']), 2)
        titles = {m['title'] for m in data['motorcycles']}
        self.assertIn("Used Bike by Field", titles)
        self.assertIn("Used Bike by M2M", titles)

    def test_response_structure_is_correct(self):
        response = self.client.get(reverse('inventory:ajax-get-motorcycle-list'), {'condition_slug': 'all'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('motorcycles', data)
        self.assertIsInstance(data['motorcycles'], list)
        if data['motorcycles']:
            first_bike = data['motorcycles'][0]
            expected_keys = [
                'id', 'title', 'brand', 'model', 'year', 'price', 'image_url', 
                'condition_display', 'engine_size', 'odometer', 'detail_url',
                'status', 'quantity', 'condition_name'
            ]
            for key in expected_keys:
                self.assertIn(key, first_bike)

