# SCOOTER_SHOP/SCOOTER_SHOP/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
# Import settings.path for the static file serving
from django.conf import settings
import os # Import os module for path joining


urlpatterns = [
    # Django Admin site URLs
    path('admin/', admin.site.urls),
    path('accounts/', include('users.urls')),
    path('inventory/', include('inventory.urls')),
    # Include service URLs with a namespace
    path('service/', include('service.urls', namespace='service')), # Added namespace
    path('hire/', include('hire.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('', include('core.urls')),
]

# Serve static and media files in development mode
# This is necessary for images, CSS, and JavaScript files to be served by Django's dev server
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=os.path.join(settings.BASE_DIR, 'static')) # Use os.path.join
    # Removed the duplicate static serving for 'static'