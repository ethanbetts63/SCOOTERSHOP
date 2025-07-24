from django.test import TestCase
from django.urls import reverse
from service.sitemaps import ServiceSitemap

class ServiceSitemapTests(TestCase):

    def test_service_sitemap_items(self):
        sitemap = ServiceSitemap()
        items = sitemap.items()
        expected_items = ["service:service", "service:service_booking_terms"]
        self.assertEqual(items, expected_items)

    def test_service_sitemap_location(self):
        sitemap = ServiceSitemap()
        for item in sitemap.items():
            location = sitemap.location(item)
            self.assertEqual(location, reverse(item))
