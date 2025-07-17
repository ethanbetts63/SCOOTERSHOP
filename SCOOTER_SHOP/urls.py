from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap

from core.sitemaps import CoreSitemap
from inventory.sitemaps import InventorySitemap, MotorcycleSitemap
from service.sitemaps import ServiceSitemap, ServiceTypeSitemap

sitemaps = {
    "core": CoreSitemap,
    "inventory": InventorySitemap,
    "motorcycles": MotorcycleSitemap,
    "service": ServiceSitemap,
    "servicetypes": ServiceTypeSitemap,
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
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
