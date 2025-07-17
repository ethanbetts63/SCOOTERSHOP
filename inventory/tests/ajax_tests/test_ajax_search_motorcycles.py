import json
from django.test import TestCase, RequestFactory
from django.urls import reverse
from inventory.ajax.ajax_search_motorcycles import search_motorcycles_ajax
from users.tests.test_helpers.model_factories import UserFactory
from inventory.tests.test_helpers.model_factories import MotorcycleFactory


class AjaxSearchMotorcyclesTest(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.factory = RequestFactory()
        cls.staff_user = UserFactory(is_staff=True)
        cls.non_staff_user = UserFactory(is_staff=False)

        cls.honda_crf = MotorcycleFactory(
            brand="Honda",
            model="CRF450R",
            status="for_sale",
            is_available=True,
            rego="HONDACRF",
        )
        cls.yamaha_yz = MotorcycleFactory(
            brand="Yamaha",
            model="YZ250F",
            status="for_sale",
            is_available=True,
            vin_number="VIN_YAMAHA",
        )
        cls.kawasaki_kx = MotorcycleFactory(
            brand="Kawasaki",
            model="KX450",
            status="reserved",
            is_available=True,
            stock_number="STOCK_KAWI",
        )

        cls.suzuki_rmz = MotorcycleFactory(
            brand="Suzuki", model="RM-Z250", status="sold", is_available=False
        )
        MotorcycleFactory(brand="KTM", model="350 SX-F", is_available=False)

    def _get_response(self, user, query_params={}):

        request = self.factory.get(
            reverse("inventory:admin_api_search_motorcycles"), query_params
        )
        request.user = user
        return search_motorcycles_ajax(request)

    def test_view_requires_staff_user(self):
        response = self._get_response(self.non_staff_user, {"query": "Honda"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(json.loads(response.content), {"status": "error", "message": "Admin access required."})

    def test_search_returns_correct_json_structure(self):
        response = self._get_response(self.staff_user, {"query": "Honda"})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("motorcycles", data)
        self.assertEqual(len(data["motorcycles"]), 1)

        motorcycle_data = data["motorcycles"][0]
        expected_keys = [
            "id",
            "title",
            "brand",
            "model",
            "year",
            "status",
            "is_available",
            "quantity",
            "condition",
            "price",
            "rego",
            "stock_number",
        ]
        for key in expected_keys:
            self.assertIn(key, motorcycle_data)

    def test_search_by_identifiers_pk_rego_vin_stock(self):

        response = self._get_response(self.staff_user, {"query": "HONDACRF"})
        data = json.loads(response.content)
        self.assertEqual(len(data["motorcycles"]), 1)
        self.assertEqual(data["motorcycles"][0]["id"], self.honda_crf.pk)

        response = self._get_response(self.staff_user, {"query": "VIN_YAMAHA"})
        data = json.loads(response.content)
        self.assertEqual(len(data["motorcycles"]), 1)
        self.assertEqual(data["motorcycles"][0]["id"], self.yamaha_yz.pk)

        response = self._get_response(self.staff_user, {"query": "STOCK_KAWI"})
        data = json.loads(response.content)
        self.assertEqual(len(data["motorcycles"]), 1)
        self.assertEqual(data["motorcycles"][0]["id"], self.kawasaki_kx.pk)

    def test_search_with_no_query_returns_empty_list(self):
        response = self._get_response(self.staff_user, {"query": ""})
        data = json.loads(response.content)
        self.assertEqual(len(data["motorcycles"]), 0)
