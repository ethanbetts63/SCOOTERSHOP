# SCOOTER_SHOP/SCOOTER_SHOP/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Define the main URL patterns for the project
urlpatterns = [
    # Django Admin site URLs
    path('admin/', admin.site.urls),
    path('accounts/', include('users.urls')),        # URLs for user auth (login, register, etc.)
    path('inventory/', include('inventory.urls')),  # URLs for motorcycle listings
    path('service/', include('service.urls')),      # URLs for service booking
    path('hire/', include('hire.urls')),            # URLs for hire booking
    path('dashboard/', include('dashboard.urls')),
    path('', include('core.urls')),
]

# Serve static and media files in development mode
# This is necessary for images, CSS, and JavaScript files to be served by Django's dev server
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.path.join(settings.BASE_DIR, 'static'))

