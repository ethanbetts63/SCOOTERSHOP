from django.test import TestCase
from django.urls import reverse
from inventory.sitemaps import InventorySitemap, MotorcycleSitemap
from inventory.tests.test_helpers.model_factories import MotorcycleFactory

class InventorySitemapTests(TestCase):

    def test_inventory_sitemap_items(self):
        sitemap = InventorySitemap()
        items = sitemap.items()
        expected_items = [
            "inventory:all",
            "inventory:new",
            "inventory:used",
            "inventory:sales_terms",
        ]
        self.assertEqual(items, expected_items)

    def test_inventory_sitemap_location(self):
        sitemap = InventorySitemap()
        for item in sitemap.items():
            location = sitemap.location(item)
            self.assertEqual(location, reverse(item))

class MotorcycleSitemapTests(TestCase):

    def setUp(self):
        self.motorcycle = MotorcycleFactory()

    def test_motorcycle_sitemap_items(self):
        sitemap = MotorcycleSitemap()
        items = sitemap.items()
        self.assertEqual(items.count(), 1)
        self.assertEqual(items.first(), self.motorcycle)

    def test_motorcycle_sitemap_location(self):
        sitemap = MotorcycleSitemap()
        location = sitemap.location(self.motorcycle)
        self.assertEqual(location, self.motorcycle.get_absolute_url())

    def test_motorcycle_sitemap_lastmod(self):
        sitemap = MotorcycleSitemap()
        lastmod = sitemap.lastmod(self.motorcycle)
        self.assertEqual(lastmod, self.motorcycle.date_posted)
