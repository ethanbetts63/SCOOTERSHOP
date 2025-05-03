# SCOOTER_SHOP/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
# Import os module for path joining if needed (already in static serving)
# import os

urlpatterns = [
    # Django Admin site URLs
    path('admin/', admin.site.urls),

    # Include app URLs with namespaces for clarity and to prevent conflicts
    # The path prefix determines where the app's URLs are included (e.g., /accounts/ for users app)
    path('accounts/', include('users.urls', namespace='users')),
    path('inventory/', include('inventory.urls', namespace='inventory')),
    path('service/', include('service.urls', namespace='service')),
    path('hire/', include('hire.urls', namespace='hire')),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),

    # Include core app URLs at the root level.
    # Use the namespace if core/urls.py defines app_name = 'core'.
    path('', include('core.urls', namespace='core')),
]

# Serve static and media files in development mode (DEBUG=True)
# In production, a dedicated web server (like Nginx or Apache) should serve these files.
if settings.DEBUG:
    # Serve user-uploaded media files
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Serve static files (CSS, JS, images collected by collectstatic)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    # Note: You had a duplicate static serving for STATIC_URL pointing to BASE_DIR / "static".
    # Using STATIC_ROOT after collectstatic is more common in DEBUG=True after running collectstatic.
    # If you have static files only in app static/ directories and want them served without collectstatic,
    # App_DIRS in TEMPLATES settings combined with the staticfiles finders handles this automatically.
    # If you have project-level static files, use STATICFILES_DIRS and then collectstatic to STATIC_ROOT.
    # The provided setup with STATICFILES_DIRS and serving STATIC_ROOT covers both.