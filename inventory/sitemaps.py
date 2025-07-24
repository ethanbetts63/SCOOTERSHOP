from django.contrib import sitemaps
from django.urls import reverse
from inventory.models import Motorcycle
import logging

class InventorySitemap(sitemaps.Sitemap):
    priority = 0.5
    changefreq = "daily"

    def items(self):
        return [
            "inventory:all",
            "inventory:new",
            "inventory:used",
            "inventory:sales_terms",
        ]

    def location(self, item):
        return reverse(item)


class MotorcycleSitemap(sitemaps.Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Motorcycle.objects.all()

    def location(self, item):
        try:
            return item.get_absolute_url()
        except Exception as e:
            logging.error(f"Error generating URL for motorcycle {item.pk}: {e}")
            return None

    def lastmod(self, obj):
        return obj.date_posted
