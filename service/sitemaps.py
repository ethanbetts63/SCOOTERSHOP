from django.contrib import sitemaps
from django.urls import reverse

class ServiceSitemap(sitemaps.Sitemap):
    priority = 0.5
    changefreq = "daily"

    def items(self):
        return ["service:service", "service:service_booking_terms"]

    def location(self, item):
        return reverse(item)