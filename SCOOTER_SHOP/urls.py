from django.contrib import admin
from django.urls import path, include, reverse_lazy
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.views.generic.base import RedirectView
from core.sitemaps import CoreSitemap
from inventory.sitemaps import InventorySitemap, MotorcycleSitemap
from service.sitemaps import ServiceSitemap

sitemaps = {
    "core": CoreSitemap,
    "inventory": InventorySitemap,
    "service": ServiceSitemap,
}

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("users.urls", namespace="users")),
    path("inventory/", include("inventory.urls", namespace="inventory")),
    path("service/", include("service.urls", namespace="service")),
    path("dashboard/", include("dashboard.urls", namespace="dashboard")),
    path("", include("core.urls", namespace="core")),
    path("payments/", include("payments.urls", namespace="payments")),
    path("refunds/", include("refunds.urls", namespace="refunds")),
    path("mailer/", include("mailer.urls", namespace="mailer")),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    # 301 Redirects
    path('showroom/', RedirectView.as_view(url=reverse_lazy('inventory:used'), permanent=True)),
    path('shop-online/', RedirectView.as_view(url=reverse_lazy('core:index'), permanent=True)),
    path('about-us/', RedirectView.as_view(url=reverse_lazy('core:contact'), permanent=True)),
    path('contact-us/', RedirectView.as_view(url=reverse_lazy('core:contact'), permanent=True)),
    path('segway-electric-scooters/', RedirectView.as_view(url=reverse_lazy('inventory:new'), permanent=True)),
    path('workshop/', RedirectView.as_view(url=reverse_lazy('service:service'), permanent=True)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
