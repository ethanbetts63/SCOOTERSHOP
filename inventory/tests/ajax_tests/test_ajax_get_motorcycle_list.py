import json
from django.test import TestCase, Client
from django.urls import reverse
from inventory.tests.test_helpers.model_factories import MotorcycleFactory


class AjaxGetMotorcycleListTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()

        # Create some motorcycles for testing
        MotorcycleFactory(
            title="New Bike 1",
            brand="Honda",
            year=2023,
            price=12000,
            engine_size=1000,
            condition="new",
            status="for_sale",
            is_available=True,
        )
        MotorcycleFactory(
            title="Used Bike 1",
            brand="Yamaha",
            year=2020,
            price=8000,
            engine_size=800,
            condition="used",
            status="for_sale",
            is_available=True,
        )
        MotorcycleFactory(
            title="New Bike 2",
            brand="Honda",
            year=2024,
            price=15000,
            engine_size=1200,
            condition="new",
            status="for_sale",
            is_available=True,
        )
        MotorcycleFactory(
            title="Demo Bike 1",
            brand="Kawasaki",
            year=2022,
            price=10000,
            engine_size=900,
            condition="demo",
            status="for_sale",
            is_available=True,
        )
        MotorcycleFactory(
            title="Sold Bike",
            brand="Suzuki",
            year=2021,
            price=9000,
            engine_size=750,
            condition="used",
            status="sold",
            is_available=False,
        )

    def test_get_all_motorcycles(self):
        response = self.client.get(
            reverse("inventory:ajax-get-motorcycle-list"), {"condition_slug": "all"}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data["motorcycles"]), 4)
        titles = [m["title"] for m in data["motorcycles"]]
        self.assertNotIn("Sold Bike", titles)

    def test_filter_by_brand(self):
        response = self.client.get(
            reverse("inventory:ajax-get-motorcycle-list"), {"brand": "Honda"}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data["motorcycles"]), 2)
        for bike in data["motorcycles"]:
            self.assertEqual(bike["brand"], "Honda")

    def test_filter_by_year(self):
        response = self.client.get(
            reverse("inventory:ajax-get-motorcycle-list"),
            {"year_min": 2022, "year_max": 2023},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data["motorcycles"]), 2)
        years = [m["year"] for m in data["motorcycles"]]
        self.assertIn(2022, years)
        self.assertIn(2023, years)

    def test_filter_by_price(self):
        response = self.client.get(
            reverse("inventory:ajax-get-motorcycle-list"),
            {"price_min": 9000, "price_max": 12000},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data["motorcycles"]), 2)
        prices = [float(m["price"]) for m in data["motorcycles"]]
        self.assertIn(10000.00, prices)
        self.assertIn(12000.00, prices)

    def test_filter_by_engine_size(self):
        response = self.client.get(
            reverse("inventory:ajax-get-motorcycle-list"),
            {"engine_min_cc": 950, "engine_max_cc": 1200},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data["motorcycles"]), 2)
        engine_sizes = [m["engine_size"] for m in data["motorcycles"]]
        self.assertIn(1000, engine_sizes)
        self.assertIn(1200, engine_sizes)

    def test_sort_by_price_low_to_high(self):
        response = self.client.get(
            reverse("inventory:ajax-get-motorcycle-list"),
            {"order": "price_low_to_high"},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        prices = [float(m["price"]) for m in data["motorcycles"]]
        self.assertEqual(prices, [8000.00, 10000.00, 12000.00, 15000.00])

    def test_sort_by_price_high_to_low(self):
        response = self.client.get(
            reverse("inventory:ajax-get-motorcycle-list"),
            {"order": "price_high_to_low"},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        prices = [float(m["price"]) for m in data["motorcycles"]]
        self.assertEqual(prices, [15000.00, 12000.00, 10000.00, 8000.00])

    def test_sort_by_year_new_to_old(self):
        response = self.client.get(
            reverse("inventory:ajax-get-motorcycle-list"), {"order": "age_new_to_old"}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        years = [m["year"] for m in data["motorcycles"]]
        self.assertEqual(years, [2024, 2023, 2022, 2020])

    def test_sort_by_year_old_to_new(self):
        response = self.client.get(
            reverse("inventory:ajax-get-motorcycle-list"), {"order": "age_old_to_new"}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        years = [m["year"] for m in data["motorcycles"]]
        self.assertEqual(years, [2020, 2022, 2023, 2024])

    def test_pagination(self):
        # Create more bikes to test pagination
        for i in range(10):
            MotorcycleFactory(title=f"Bike {i}", is_available=True, status="for_sale")

        response = self.client.get(
            reverse("inventory:ajax-get-motorcycle-list"), {"page": 1}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data["motorcycles"]), 9)
        self.assertTrue(data["page_obj"]["has_next"])

        response = self.client.get(
            reverse("inventory:ajax-get-motorcycle-list"), {"page": 2}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(
            len(data["motorcycles"]), 5
        )  # 4 from setUpTestData + 10 here = 14 total. 9 on page 1, 5 on page 2
        self.assertFalse(data["page_obj"]["has_next"])
