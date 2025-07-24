from django.test import TestCase
from django.urls import reverse
from core.sitemaps import CoreSitemap

class CoreSitemapTests(TestCase):

    def setUp(self):
        self.sitemap = CoreSitemap()

    def test_sitemap_items(self):
        items = self.sitemap.items()
        expected_items = [
            "core:index",
            "core:contact",
            "core:privacy",
            "core:returns",
            "core:security",
            "core:terms",
        ]
        self.assertEqual(items, expected_items)

    def test_sitemap_location(self):
        for item in self.sitemap.items():
            location = self.sitemap.location(item)
            self.assertEqual(location, reverse(item))
