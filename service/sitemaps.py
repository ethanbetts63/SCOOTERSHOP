from django.contrib import sitemaps
from django.urls import reverse
from .models import ServiceType

class ServiceSitemap(sitemaps.Sitemap):
    priority = 0.5
    changefreq = 'daily'

    def items(self):
        return ['service:service', 'service:service_booking_terms']

    def location(self, item):
        return reverse(item)

class ServiceTypeSitemap(sitemaps.Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return ServiceType.objects.all()
