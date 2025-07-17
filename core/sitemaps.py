from django.contrib import sitemaps
from django.urls import reverse


class CoreSitemap(sitemaps.Sitemap):
    priority = 0.5
    changefreq = "daily"

    def items(self):
        return [
            "core:index",
            "core:contact",
            "core:privacy",
            "core:returns",
            "core:security",
            "core:terms",
        ]

    def location(self, item):
        return reverse(item)
