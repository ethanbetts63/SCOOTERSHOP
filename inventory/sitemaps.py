from django.contrib import sitemaps
from django.urls import reverse
from .models import Motorcycle


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

    def lastmod(self, obj):
        return obj.updated_at
